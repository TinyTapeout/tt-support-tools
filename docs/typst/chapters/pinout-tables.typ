#let caravel = {
  align(center,
    table(
      columns: 4,
      align: left,
      table.header(
        [mprj_io_pin], [Function], [Signal], [QFN64 pin]
      ),

      `0`, [Input], [`ui_in[0]`], [`31`],
      `1`, [Input], [`ui_in[1]`], [`32`],
      `2`, [Input], [`ui_in[2]`], [`33`],
      `3`, [Input], [`ui_in[3]`], [`34`],
      `4`, [Input], [`ui_in[4]`], [`35`],
      `5`, [Input], [`ui_in[5]`], [`36`],
      `6`, [Input], [`ui_in[6]`], [`37`],
      `7`,  [Analog], [`analog[0]`], [`41`],
      `8`,  [Analog], [`analog[1]`], [`42`],
      `9`,  [Analog], [`analog[2]`], [`43`],
      `10`, [Analog], [`analog[3]`], [`44`],
      `11`, [Analog], [`analog[4]`], [`45`],
      `12`, [Analog], [`analog[5]`], [`46`],
      `13`, [Input], [`ui_in[7]`], [48],
      `14`, [Input], [`clk` $dagger$], [50],
      `15`, [Input], [`rst_n` $dagger$], [`51`],
      `16`, [Bidirectional], [`uio[0]`], [`53`],
      `17`, [Bidirectional], [`uio[1]`], [`54`],
      `18`, [Bidirectional], [`uio[2]`], [`55`],
      `19`, [Bidirectional], [`uio[3]`], [`57`],
      `20`, [Bidirectional], [`uio[4]`], [`58`],
      `21`, [Bidirectional], [`uio[5]`], [`59`],
      `22`, [Bidirectional], [`uio[6]`], [`60`],
      `23`, [Bidirectional], [`uio[7]`], [`61`],
      `24`, [Output], [`uo_out[0]`], [`62`],
      `25`, [Output], [`uo_out[1]`], [`2`],
      `26`, [Output], [`uo_out[2]`], [`3`],
      `27`, [Output], [`uo_out[3]`], [`4`],
      `28`, [Output], [`uo_out[4]`], [`5`],
      `29`, [Output], [`uo_out[5]`], [`6`],
      `30`, [Output], [`uo_out[6]`], [`7`],
      `31`, [Output], [`uo_out[7]`], [`8`],
      `32`, [Analog], [`analog[6]`], [`11`],
      `33`, [Analog], [`analog[7]`], [`12`],
      `34`, [Analog], [`analog[8]`], [`13`],
      `35`, [Analog], [`analog[9]`], [`14`],
      `36`, [Analog], [`analog[10]`], [`15`],
      `37`, [Analog], [`analog[11]`], [`16`],
      `38`, [Mux Control], [`ctrl_ena`], [`22`],
      `39`, [Mux Control], [`ctrl_sel_inc`], [`24`],
      `40`, [Mux Control], [`ctrl_sel_rst_n`], [`25`],
      `41`, [Reserved], [(none)], [`26`],
      `42`, [Reserved], [(none)], [`27`],
      `43`, [Reserved], [(none)], [`28`],
    )
  )

  [
    $dagger$ Internally, there's no difference between `clk`, `rst_n` and `ui_in` pins. They are all just bits in the 
    `pad_ui_in` bus. However, we use different names to make it easier to understand the purpose of each signal.
  ]
}

#let openframe = {
  align(center, 
    table(
      columns: 3,
      align: left,

      table.header(
        [QFN64 Pin], [Function], [Signal]
      ),

      `1`, [Mux Control], [`ctrl_ena`],
      `2`, [Mux Control], [`ctrl_sel_inc`],
      `3`, [Mux Control], [`ctrl_sel_rst_n`],
      `4`, [Reserved], [(none)],
      `5`, [Reserved], [(none)],
      `6`, [Reserved], [(none)],
      `7`, [Reserved], [(none)],
      `8`, [Reserved], [(none)],
      `9`, [Output], [`uo_out[0]`],
      `10`, [Output], [`uo_out[1]`],
      `11`, [Output], [`uo_out[2]`],
      `12`, [Output], [`uo_out[3]`],
      `13`, [Output], [`uo_out[4]`],
      `14`, [Output], [`uo_out[5]`],
      `15`, [Output], [`uo_out[6]`],
      `16`, [Output], [`uo_out[7]`],
      `17`, [Power], [VDD IO],
      `18`, [Ground], [GND IO],
      `19`, [Analog], [`analog[0]`],
      `20`, [Analog], [`analog[1]`],
      `21`, [Analog], [`analog[2]`],
      `22`, [Analog], [`analog[3]`],
      `23`, [Power], [VAA Analog],
      `24`, [Ground], [GND Analog],
      `25`, [Analog], [`analog[4]`],
      `26`, [Analog], [`analog[5]`],
      `27`, [Analog], [`analog[6]`],
      `28`, [Analog], [`analog[7]`],
      `29`, [Ground], [VDD Core],
      `30`, [Power], [VDD Core],
      `31`, [Ground], [GND IO],
      `32`, [Power], [VDD IO],
      `33`, [Bidirectional], [`uio[0]`],
      `34`, [Bidirectional], [`uio[1]`],
      `35`, [Bidirectional], [`uio[2]`],
      `36`, [Bidirectional], [`uio[3]`],
      `37`, [Bidirectional], [`uio[4]`],
      `38`, [Bidirectional], [`uio[5]`],
      `39`, [Bidirectional], [`uio[6]`],
      `40`, [Bidirectional], [`uio[7]`],
      `41`, [Input], [`ui_in[0]`],
      `42`, [Input], [`ui_in[1]`],
      `43`, [Input], [`ui_in[2]`],
      `44`, [Input], [`ui_in[3]`],
      `45`, [Input], [`ui_in[4]`],
      `46`, [Input], [`ui_in[5]`],
      `47`, [Input], [`ui_in[6]`],
      `48`, [Input], [`ui_in[7]`],
      `49`, [Input], [`rst_n` $dagger$],
      `50`, [Input], [`clk` $dagger$],
      `51`, [Ground], [GND IO],
      `52`, [Power], [VDD IO],
      `53`, [Analog], [`analog[8]`],
      `54`, [Analog], [`analog[9]`],
      `55`, [Analog], [`analog[10]`],
      `56`, [Analog], [`analog[11]`],
      `57`, [Ground], [GND Analog],
      `58`, [Power], [VDD Analog],
      `59`, [Analog], [`analog[12]`],
      `60`, [Analog], [`analog[13]`],
      `61`, [Analog], [`analog[14]`],
      `62`, [Analog], [`analog[15]`],
      `63`, [Ground], [GND Core],
      `64`, [Power], [VDD Core]
   )
  )

  [
    $dagger$ Internally, there's no difference between `clk`, `rst_n` and `ui_in` pins. They are all just bits in the 
    `pad_ui_in` bus. However, we use different names to make it easier to understand the purpose of each signal.
  ]
}