#import "../src/lib.typ": annotated_qrcode

#let call_to_action_page(qrcode_colour: black) = [
  #align(center)[
    #heading(level: 1)[Where is #emph(underline("your")) design?]
    *Go from idea to chip design in minutes, without breaking the bank.*
  ]

  Interested and want to get your own design manufactured? Visit our website and
  check out our educational material and previous submissions!

  #align(center, heading(level: 2, outlined: false)[How?])
  New to this? Use our basic Wokwi template to see what's possible. If you're ready for more,
  use our advanced Wokwi template and unlock some extra pins.

  Know Verilog and CocoTB? Get stuck in with our HDL templates.

  #align(center, heading(level: 2, outlined: false)[When?])
  Multiple shuttles are run per year, meaning you've got an opportunity to manufacture your design
  at any time.

  #align(center, heading(level: 2, outlined: false)[Stuck? Need help? Want inspiration?])
  Come chat to us and our community on Discord! Scan the QR code below.

  #v(1cm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    rows: 1,
    column-gutter: 1em,
    align: center,
    inset: 8pt,
    fill: white,

    annotated_qrcode(
      "https://tinytapeout.com", 
      "Website", 
      tiaoma_args: ("scale": 2.0, "fg-color": qrcode_colour)
    ),

    annotated_qrcode(
      "https://tinytapeout.com/digital_design", 
      "Digital design guide", 
      tiaoma_args: ("scale": 1.75, "fg-color": qrcode_colour)
    ),

    annotated_qrcode(
      "https://tinytapeout.com/discord", 
      "Discord server", 
      tiaoma_args: ("scale": 2.0, "fg-color": qrcode_colour)
    )
  )
]