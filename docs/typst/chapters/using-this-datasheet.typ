#import "../src/lib.typ": badge, callout
#import "../src/colours.typ"

= Using This Datasheet

== Structure
Projects are ordered by their mux address, in ascending order. Documentation is user-provided from their GitHub
repositories and are merged into the final shuttle once the deadline is reached.

In general, each project should contain:
- The user-provided title & a list of authors
- A link to the GitHub repository used for submission
- A link to the Wokwi project (if applicable)
- A "How it works" section
- A "How to test" section
- An "External hardware" section (if applicable)
- A pinout table for both digital & analog designs

== Badges
This datasheet uses "badges" to quickly convey some information about the content. These badges are explained in the 
table below.

#let example_address_badge = box(baseline: 0.4em, badge(colours.BADGE_TEAL, strong(raw("-123"))))
#let example_microtile_addr_badge = box(baseline: 0.4em, badge(colours.BADGE_TEAL, strong(raw("-423/2"))))
#let example_clock_badge = box(baseline: 0.4em, badge(colours.BADGE_BLUE, strong(raw("25.175 MHz"))))
#let example_proj_wokwi = box(baseline: 0.4em, badge(colours.BADGE_PINK, strong(raw("Wokwi Project"))))
#let example_proj_hdl = box(baseline: 0.4em, badge(colours.BADGE_PINK, strong(raw("HDL Project"))))
#let example_proj_analog = box(baseline: 0.4em, badge(colours.BADGE_PINK, strong(raw("Analog Project"))))
#let example_proj_analog = box(baseline: 0.4em, badge(colours.BADGE_PINK, strong(raw("Analog Project"))))
#let example_medium_danger = box(baseline: 0.4em, badge(colours.WARNING_STRONG, strong(raw("Medium Danger"))))
#let example_high_danger = box(baseline: 0.4em, badge(colours.DANGER_STRONG, strong(raw("High Danger"))))
#let example_artwork = box(baseline: 0.4em, badge(colours.BADGE_PURPLE, strong(raw("Artwork"))))



#table(
  columns: 2,
  inset: 6pt,
  align: (center + horizon, left),

  table.header(
    [Badge], [Description]
  ),

  example_artwork, [Used to showcase artwork from our community.],

  [#example_address_badge \ #example_microtile_addr_badge], [Mux address of the project, in decimal. For microtile 
  designs, their sub-address is placed after the forward slash. In this example, it would be `2`.],

  example_clock_badge, [Clock frequency of the project. May be truncated from actual value or omitted completely.],

  [#example_proj_hdl \ #example_proj_wokwi \ #example_proj_analog], [Project type, indicating if it was made with a HDL,
  Wokwi, or if it is analog.],
  
  [#example_medium_danger \ #example_high_danger], [Indicates the risk that the project presents to the ASIC. Medium 
  danger projects can damage the ASIC under certain conditions, whilst high danger projects _will_ damage the ASIC.]
)

== Callouts
In addition to #example_medium_danger and #example_high_danger badges being used, a callout is placed before the project
documentation begins to alert the user.

A callout for #example_medium_danger may look something like:
#callout("warning", 
  `This project will damage the ASIC under certain conditions.`, 
  `There is an error in the schematic which may lead to ASIC failure under certain clocking conditions.`
)

Similarly, a callout for #example_high_danger may look something like:
#callout("danger",
  `This project will damage the ASIC.`,
  `There is an error in the schematic which may cause permanent damage when powered on in a certain configuration.`
)

Should there be a project that poses a danger, the callout will explain the reasoning behind the danger level.

Callouts may also provide some additional information, and look something like so:
#callout("info",
  `Information`,
  raw("Silicon melts at 1414°C, and boils at 3265°C. Don't let your chip get too hot!")
)

== Figures & Footnotes
Numbering for figures and footnotes within the "Project" chapter is formed by combining the address of the project with 
the current figure number. For example, the second figure for a project with an address of 256 will be captioned with 
"Figure 256.2". Likewise, the third footnote for a project of address 128 will be shown as "128.3".

The numbering outside of the "Project" chapter resumes as normal, being formatted with a simple number, e.g. "Figure 3".

== Updates
This datasheet is intended to be a living and breathing document. Please update your projects' datasheet with new 
information if you have it, by creating a pull request against the shuttle repository.