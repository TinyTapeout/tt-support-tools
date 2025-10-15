#import "@preview/tiaoma:0.3.0"
#import "colours.typ" as colours

/// Create a badge with a given colour and text
///
/// NOTE: This function will replace any instances of a hyphen ("-")
/// with a coloured zero digit. This is intended, and is used for
/// the address badge.
/// - colour (color): Colour of the badge
/// - doc (content, str): Text to display within the badge
/// -> content
#let badge(colour, body) = {
  set text(white)
  show "-": text(colours.BADGE_MUTED_TEAL, "0")
  rect(fill: colour, body)
}

/// Create a callout to display important information
///
/// - type (): Callout type (warning, danger, info, custom)
/// - title (str): Title of the callout
/// - custom_title_colour (color): Colour to use for the title of the custom callout
/// - custom_body_colour (color): Colour to use for the body of the custom callout
/// - body (content, str): Content to display in the body of the callout
/// -> content
#let callout(
  type,
  title,
  custom_title_colour: none,
  custom_body_colour: none,
  body
) = {

  set par(justify: false)
  let title_colour
  let body_colour

  if type == "warning" {
    title_colour = colours.WARNING_STRONG
    body_colour = colours.WARNING_WEAK

  } else if type == "danger" {
    title_colour = colours.DANGER_STRONG
    body_colour = colours.DANGER_WEAK

  } else if type == "info" {
    title_colour = colours.INFO_STRONG
    body_colour = colours.INFO_WEAK

  } else if type == "custom" {
    title_colour = custom_title_colour
    body_colour = custom_body_colour

  } else {
    panic([unknown callout type (#type)])
  }

  set text(white)

  // make body first
  block(
    fill: body_colour,
    width: 100%,
    inset: 8pt,

    {
      // make title
      block(fill: title_colour, width: 100%, outset: 8pt, strong(title))
      body
    }
  )
}

/// Create an annotated QR code
///
/// An annotated QR code consists of a title, the QR code, and the link to the website.
/// They are stacked on top of each other.
///
/// - url (str): Link to a website
/// - title (str): Title of the QR code
/// - title_colour (color): Colour of the title of the QR code
/// - url_colour (color): Colour of the link
/// - tiaoma_args (dict): Arguments to pass to the tiaoma package
/// -> grid
#let annotated_qrcode(
  url,
  title,
  title_colour: black,
  url_colour: black,
  tiaoma_args: (:)
) = {
  let qr = tiaoma.qrcode(url, options: tiaoma_args)

  grid(
    columns: 1,
    rows: 3,
    align: center + horizon,
    row-gutter: 1em,

    text(fill: title_colour, title),
    qr,

    // make url be the width of the QR code
    context {
      block(
        width: measure(qr).width + 1cm,
        height: auto,
        breakable: false,
        link(url, text(url_colour, url.trim("https://", at: start))))
    }
  )
}

/// Retrieve an image from via an ID
///
/// The artwork repo must be cloned into resources/external, and its `manifest.yaml`
/// must be present for this function to work.
///
/// - type (str): Type of image to fetch (must be a key in one of the manifests)
/// - id (str): ID of image to fetch
/// - args (arguments): Arguments to supply to `image()`
/// -> content
#let get_image_by_id(type, id, ..args) = {

  // external manifest is used for artwork repo
  // since large photos would bloat the template size
  let manifest = yaml("../resources/external/manifest.yaml")

  if type not in manifest {
    panic("type not in manifest")
  }

  let root_path = "../resources/external"
  let img_details = manifest.at(type).at(id)

  // make image
  image(root_path + "/" + type + "/" + img_details.file, ..args)
}

/// Create a horizontal line
///
/// Used for `pandoc` compatability
///
/// -> content
#let horizontalrule() = {
  line(
    length: 100%,
    stroke: 2pt + colours.HORIZONTAL_RULE_GREY
  )
}

/// Create a block quote
///
/// Used for `pandoc` compatability
///
/// - body (content): Body of the block quote
/// -> content
#let blockquote(body) = {
  quote(
    block: true,
    body
  )
}