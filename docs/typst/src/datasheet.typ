#import "@preview/tiaoma:0.3.0"

#import "lib.typ": badge, callout, annotated_qrcode, get_image_by_id
#import "colours.typ"

#import "../chapters/pinout-tables.typ" as pins
#import "../chapters/call-to-action.typ": call_to_action_page

#let _funding_content = state("_funding_content", [])
#let _funding_alt_title = state("_funding_alt_title", [])
#let _flip_footer_ordering = state("_flip_footer_ordering", false)
#let _chip_render_content = state("_chip_render_content", none)
#let _chip_render_sponsor_text = state("_chip_render_sponsor_text", none)
#let _chip_render_sponsor_logo = state("_chip_render_sponsor_logo", none)

#let styling(body) = {
  set page(paper: "a4", margin: auto)
  set text(font: "Montserrat", size: 12pt)
  show raw: set text(font: "Martian Mono", weight: "light")

  // style headings
  show heading.where(level: 1): this => {
    text(size: 28pt, this)
    v(0.1cm)
  }
  show heading.where(level: 2): set text(size: 22pt)
  show heading.where(level: 3): set text(size: 16pt)

  // indent numbered and bullet point lists
  set enum(indent: 1em)
  set list(indent: 1em)

  // format table so that empty cells show dark grey em dash
  show table.cell: this => {
    if this.body == [] {
        align(center + horizon, text(fill: colours.TABLE_GREY)[$dash.em$])
    } else {
      this
    }
  }

  // set quote styling
  // used for project description
  show quote: set align(center)
  show quote: set pad(x: 1em)
  show quote: set block(above: 1.75em)

  body
}

#let styling_set_par(body) = {
  // justify text, except for in tables
  set par(justify: true)
  show table: this => {
    set par(justify: false)
    this
  }
  body
}

#let _footer(shuttle, invert_text_colour: false, display_pg_as: "1", flip_ordering: false) = {
  // setup
  set text(size: 10pt)
  set text(white) if invert_text_colour

  let logo = box(baseline: 0.25em, {
    if invert_text_colour {
      image("../resources/logos/tt-logo-white.svg", height: 25%)
    } else {
      image("../resources/logos/tt-logo-black.svg", height: 25%)
    }
  })

  // get the title of the current chapter
  let title = context query(selector(heading.where(level: 1)).before(here())).last().body
  let pg_num = context counter(page).display(display_pg_as)

  let TITLE_SPACING = 0.5cm
  let LOGO_SPACING = 0.25cm

  let set_1 = {strong(pg_num); h(TITLE_SPACING); emph(title);  h(1fr);  emph(shuttle); h(LOGO_SPACING); logo}
  let set_2 = {logo; h(LOGO_SPACING); emph(shuttle);  h(1fr);  emph(title); h(TITLE_SPACING); strong(pg_num)}

  // actual styling
  context {
    // alternate odd-even pages
    if calc.even(counter(page).get().first()) {
      if flip_ordering {set_2} else {set_1}
    } else {
      if flip_ordering {set_1} else {set_2}
    }
  }
}

#let project(
  title: "Title",
  author: ("Author 1", "Author 2"),
  repo_link: "!!! missing repository link !!!",
  description: "!!! Missing description !!!",
  address: "----",
  clock: "No Clock",
  type: "HDL",
  wokwi_id: none,
  danger_level: none,
  danger_reason: none,

  body
) = {

  show: styling;
  show: styling_set_par;

  // make fake heading - this is the one that gets shown in the table of contents
  // which has the nice address marker next to it
  let fake_heading = block(
    heading(level: 2, outlined: true, bookmarked: false)[
      #box(baseline: 0.4em, badge(colours.BADGE_TEAL, strong(raw(address))))
      #title
    ]
  )

  // move fake heading so it doesn't affect layout
  place(top + left, hide(fake_heading))

  // make heading thats seen on the project page
  heading(level: 2, outlined: false, bookmarked: true, title)

  // display author names
  // if 1, it is displayed as is
  // if 2, it is displayed as "a & b"
  // if >2, it is displayed as "a, b & c"
  let author_text = []
  author_text += [by *#author.at(0)*]

  if author.len() == 2 {
    author_text += [ & *#author.at(1)*]

  } else if author.len() > 2 {
    let names = author.slice(1, author.len()-1)

    for name in names {
      author_text += [, *#name*]
    }

    author_text += [ & *#author.at(author.len()-1)*]
  }
  author_text

  // makes badges array, add address first
  let badges = (badge(colours.BADGE_TEAL, strong(raw(address))),)
  if clock != "No Clock" {badges.push(badge(colours.BADGE_BLUE, strong(raw(clock))))}
  badges.push(badge(colours.BADGE_PINK, strong(raw(type + " Project"))))

  // add asic danger callout if necessary
  let danger_callout
  if danger_level != none {
    if danger_level == "medium" {
      badges.push(badge(colours.WARNING_STRONG, strong(raw("Medium Danger"))))
      danger_callout = callout(
        "warning",
        raw("This project can damage the ASIC under certain conditions."),
        raw(danger_reason)
      )

    } else if danger_level == "high" {
      badges.push(badge(colours.DANGER_STRONG, strong(raw("High Danger"))))
      danger_callout = callout(
        "danger",
        raw("This project will damage the ASIC."),
        raw(danger_reason)
      )
    } else {
      panic([unexpected danger_level value (#danger_level)])
    }
  }

  // add badges to page, unpack badge array
  grid(columns: badges.len(), column-gutter: 1em, ..badges)

  // hardcode these repo/wokwi links to be black and to not follow link-override-colour
  link(repo_link, text(black, raw(repo_link.trim("https://", at: start))))

  if wokwi_id != none {
    let wokwi_link = "https://wokwi.com/projects/" + wokwi_id
    parbreak()
    link(wokwi_link, text(black, raw(wokwi_link.trim("https://", at: start))))
  }

  // add description and danger callout to page
  quote(block: true, quotes: true, emph(description))
  danger_callout

  set heading(offset: 2)

  // ensure each figure and footnote is only counted within its project
  // format numbering as "<project_address>.<figure_count>"
  let project_numbering(count) = {address.trim("-", at: start) + "." + str(count)}

  counter(figure.where(kind: image)).update(0)
  counter(footnote).update(0)
  set figure(numbering: project_numbering)
  set footnote(numbering: project_numbering)

  body
  pagebreak(weak: true)
}

#let splash_chapter_page(
  title,
  page_colour: white,
  invert_text_colour: false,
  footer_text: none,
  additional_content: none
) = {

  page(
    fill: page_colour,
    footer: context {
      _footer(
        footer_text,
        invert_text_colour: invert_text_colour,
        flip_ordering: _flip_footer_ordering.final()
      )
    },

    // page body - center title and add additional content if necessary
    {
      set text(white) if invert_text_colour

      // make headings
      align(center + horizon, block(text(size: 100pt, strong(title))))
      place(top + left, hide(heading(level: 1, title)))

      // make info box if needed
      if additional_content != none {
        set text(black)
        place(center + bottom, block(fill: white, inset: 10pt, additional_content))
      }
    }
  )
}

// make a tiling logo page
#let tiling_logo_page() = {

  let pattern = tiling(
    size: (3cm, 3cm),
    spacing: (1cm, 1cm),
    image("../resources/logos/tt-logo-light-grey.svg")
  )

  page(
    background: rect(width: 110%, height: 105%, inset: 0pt, outset: 0pt, stroke: none, fill: pattern),
    [] // empty page
  )
}

#let datasheet(
  shuttle_id: none,
  shuttle_name: none,
  repo_link: none,
  theme: "classic",
  projects: none,
  show_pinouts: "openframe",
  theme_override_colour: none,
  date: datetime.today(),
  link_disable_colour: false,
  link_override_colour: none,
  chip_viewer_link: none,
  qrcode_follows_theme: false,

  body
) = {

  set document(
    title: [#shuttle_name Datasheet],
    author: "Tiny Tapeout & Contributors",
    description: [The official Tiny Tapeout datasheet for #shuttle_id. Template by Kristaps Jurkans (bluesky/\@krisj.dev)]
  )

  show: styling;

  let date_str = date.display("[month repr:long] [day padding:none], [year]")

  // contains title, repo link and compilation date
  let cover_text = align(center)[
    #text(size: 32pt, strong[#shuttle_name Datasheet])

    #link(
      repo_link,
      text(
        size: 14pt,
        font: "Martian Mono",
        repo_link.trim("https://", at: start)
      )
    )

    #v(2.5cm)
    #text(size: 16pt, weight: "medium", date_str)
  ]


  // configure theme variables
  let selected_theme_colour = colours.THEME_PLUM // default fill
  if theme_override_colour != none {selected_theme_colour = theme_override_colour}

  let qrcode_colour = black
  if qrcode_follows_theme and theme == "bold" {qrcode_colour = selected_theme_colour}

  // make titlepage
  if theme == "classic" {
    image("../resources/logos/tt-logo-colourful.png")
    cover_text

  } else if theme == "bold" {
    set page(
      background: image("../resources/backgrounds/colourful-background-gds-o10-bw.png", height: 100%),
      fill: selected_theme_colour
    )

    align(
      center + horizon,
      image("../resources/logos/tt-logo-white.svg", height: 60%)
    )

    set text(white)
    cover_text

  } else if theme == "monochrome" {
    align(
      center + horizon,
      image("../resources/logos/tt-logo-black.svg", height: 60%)
    )
    cover_text
  }

  // style link colour
  // moved after title page since theme-override-colour would cause it to blend in with the background
  let link_colour = luma(0%)
  if not link_disable_colour {
    // if override colour specified, set it to that
    // else fall back to default link colour
    if link_override_colour != none {
      link_colour = link_override_colour
    } else {
      link_colour = colours.LINK_DEFAULT
    }
  }
  show link: set text(link_colour)

  // add tiling logo page (this is pg2 of the datasheet)
  tiling_logo_page()

  show: styling_set_par;

  // setup for table of contents
  set page(footer: _footer(shuttle_id, invert_text_colour: false, display_pg_as: "i"))
  counter(page).update(1)
  // add spacing for each H1, and make H1 bold
  show outline.entry.where(level: 1): set block(above: 1em)
  show outline.entry.where(level: 1): strong

  // make actual table of contents
  outline(
    depth: 2,
    title: heading(level: 1, outlined: false, bookmarked: true, "Table of Contents")
  )
  pagebreak(weak: true)

  // determine whether we need to flip the footer ordering depending on if the table fo contents
  // ended on an odd or even page
  context {
    _flip_footer_ordering.update(calc.even(counter(page).get().last()))
  }

  set page(footer: context {_footer(
    shuttle_id, display_pg_as: "1", flip_ordering: _flip_footer_ordering.final()
  )})

  // reset page counter so that it starts counting actual content now
  counter(page).update(1)

  // make chip render pages
  context {
    let chip_renders = _chip_render_content.final()

    if chip_renders != none {
      let qr
      let qr_grid

      if chip_viewer_link != none {
        qr_grid = annotated_qrcode(
          chip_viewer_link, "Online chip viewer",
          tiaoma_args: ("scale": 2.0, "fg-color": qrcode_colour)
        )
      }


      let sponsor_grid
      if _chip_render_sponsor_text.final() != none and _chip_render_sponsor_logo.final() != none {
        sponsor_grid = grid(
          columns: 1,
          rows: 3,
          align: center + horizon,
          row-gutter: 1em,

          _chip_render_sponsor_text.final(),
          _chip_render_sponsor_logo.final(),
          [] // added for padding
        )
      }

      let content
      let content_arr = ()

      if sponsor_grid != none {
        content_arr.push(sponsor_grid)
      }

      if qr_grid != none {
        content_arr.push(qr_grid)
      }

      if content_arr.len() >= 1 {
        content = grid(
          columns: content_arr.len(),
          rows: 1,
          column-gutter: 1em, row-gutter: 1em,
          align: center + horizon,

          ..content_arr
        )
      }

      if theme == "bold" {
        splash_chapter_page(
          "Chip Renders", 
          page_colour: selected_theme_colour, 
          invert_text_colour: true, 
          footer_text: shuttle_id, 
          additional_content: content
        )
      } else {
        splash_chapter_page(
          "Chip Renders",
          invert_text_colour: false,
          footer_text: shuttle_id,
           additional_content: content
        )
      }
      // display chip renders
      chip_renders
    }
  }

  // make project splash page + show all projects
  if projects != none {
    if theme == "bold" {
      splash_chapter_page(
        "Projects", 
        page_colour: selected_theme_colour,
        invert_text_colour: true,
        footer_text: shuttle_id
      )
    } else {
      splash_chapter_page(
        "Projects", 
        footer_text: shuttle_id
      )
    }
    projects
  }

  // reset counters back to 0, to be used in the info section of the datasheet
  counter(figure.where(kind: image)).update(0)
  counter(footnote).update(0)
  body

  // add informational content
  // chip pinout diagram
  page(include "../chapters/pinout.typ")

  // multiplexer infrastructure explanation
  page({
    include "../chapters/tt-multiplexer.typ"

    if show_pinouts == "caravel" {
      pins.caravel
    } else if show_pinouts == "openframe" {
      pins.openframe
    } else {
      panic([unknown pinout table referenced (#show_pinouts)])
    }
  })

  // add funding/sponsor page
  page(context {
    let funding_content = _funding_content.final()
    let alt_title = _funding_alt_title.final()

    if funding_content != [] {
      if alt_title != none {
        heading(level: 1, alt_title)
      } else {
        heading(level: 1, "Funding")
      }
    }

    funding_content
  })

  page(include "../chapters/team.typ")
  page(include "../chapters/using-this-datasheet.typ")

  // add call to action page
  if theme == "classic" or theme == "monochrome" {
    page(call_to_action_page())
  } else if theme == "bold" {
    page(
      fill: selected_theme_colour,
      footer: none,
      {
        set text(white)
        call_to_action_page(qrcode_colour: black)
      }
    )
  }
}

#let funding(doc, alt_title: none) = {
  context {
    _funding_content.update(doc)
    _funding_alt_title.update(alt_title)
  }
}

#let renders(sponsor_text: none, sponsor_logo: none, doc) = {
  context {
    _chip_render_content.update(doc)
    _chip_render_sponsor_text.update(sponsor_text)
    _chip_render_sponsor_logo.update(sponsor_logo)
  }
}

#let art(id, rot: 90deg) = {

  // all artwork is assumed to be external (hosted in a separate repo)
  let art_img = get_image_by_id("artwork", id, height: 100%)
  let info = yaml("../resources/external/manifest.yaml").at("artwork").at(id)

  let attribution = strong[
    #info.title $dash.fig$
    #if info.at("designer", default: none) != none [Designed by #info.designer.]
    Illustrated by #info.artist.
  ]

  // heading shown in table of contents
  let art_heading = [#box(baseline: 0.4em, badge(colours.BADGE_PURPLE, strong(`Artwork`))) #info.title]
  set text(fill: white, size: 10pt)

  page(
    paper: "a4",
    margin: 0pt,
    footer: none,
    // add artwork as background
    background: rotate(rot, reflow: true, art_img),
    {
      // make fake & read heading
      // first is shown in ToC, the second in the PDF list
      place(top, hide(heading(level: 2, outlined: true, bookmarked: false, art_heading)))
      place(top, hide(heading(level: 2, outlined: false, bookmarked: true)[(Artwork) #info.title]))

      // determine position for artwork attribution
      context {
        let attribution_placement = bottom + left

        // if even
        if calc.even(counter(page).get().first()) {
          // but flipped
          if _flip_footer_ordering.final() {
            attribution_placement = bottom + right
          } else {
            attribution_placement = bottom + left
          }

        // if odd
        } else {
          if _flip_footer_ordering.final() {
            attribution_placement = bottom + left
          } else {
            attribution_placement = bottom + right
          }
        }

        // add artwork attribution
        place(
          attribution_placement,
          block(
            fill: colours.ARTWORK_GREY_INFO,
            inset: 4pt,
            attribution
          )
        )
      }
    }
  )
}

#let add_render(title, subtitle: none, img) = {
  page(
    align(center, grid(
        columns: 1,
        row-gutter: 10pt,
        align: center,

        heading(level: 2, title),
        subtitle,
        img
      )
    )
  )
}