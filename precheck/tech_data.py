# fmt: off
valid_layers_sky130A = [
    'cldntm.mask', 'ldntm.drawing', 'cncm.mask', 'ctunm.mask', 'cnwm.mask', 'cnsm.mask', 'cfom.drawing', 'cfom.maskAdd',
    'cfom.maskDrop', 'cfom.waffleDrop', 'cfom.mask', 'clvtnm.mask', 'cntm.drawing', 'cntm.mask', 'cp1m.mask',
    'cnsdm.drawing', 'cnsdm.maskAdd', 'cnsdm.maskDrop', 'cnsdm.mask', 'cpsdm.drawing', 'cpsdm.maskAdd', 'cpsdm.maskDrop',
    'cpsdm.mask', 'cp1m.waffleDrop', 'cp1m.maskDrop', 'cp1m.maskAdd', 'cmm3.mask', 'cctm1.mask', 'cmm1.mask', 'cpdm.mask',
    'chvntm.drawing', 'chvntm.mask', 'cviam.mask', 'cmm2.mask', 'clicm1.mask', 'cviam2.mask', 'pwelliso.label',
    'pwelliso.pin', 'cnpc.drawing', 'clvom.drawing', 'clvom.mask', 'cdnm.mask', 'cnpc.mask', 'cviam3.mask', 'cmm4.mask',
    'crpm.maskDrop', 'crpm.maskAdd', 'crpm.drawing', 'cli1m.mask', 'cviam4.mask', 'cmm5.mask', 'nsm.drawing',
    'cmm1.waffleDrop', 'nwell.label', 'pwell.res', 'pwell.cut', 'nwell.pin', 'dnwell.drawing', 'nwell.drawing',
    'pwell.drawing', 'pwell.label', 'diff.hv', 'diff.res', 'diff.cut', 'diff.drawing', 'tap.drawing', 'poly.boundary',
    'poly.label', 'poly.gate', 'poly.res', 'poly.cut', 'poly.short', 'poly.pin', 'poly.drawing', 'poly.net', 'poly.probe',
    'licon1.net', 'licon1.drawing', 'licon1.boundary', 'poly.model', 'li1.boundary', 'li1.label', 'li1.blockage',
    'li1.short', 'li1.pin', 'li1.drawing', 'li1.net', 'li1.probe', 'mcon.net', 'mcon.drawing', 'mcon.boundary',
    'met1.boundary', 'met1.label', 'met1.blockage', 'met1.short', 'met1.pin', 'met1.drawing', 'met1.net', 'met1.probe',
    'via.net', 'via.drawing', 'via.boundary', 'met1.psa1', 'met1.psa2', 'met1.psa3', 'met1.psa4', 'met1.psa5', 'met1.psa6',
    'met2.boundary', 'met2.label', 'met2.blockage', 'met2.short', 'met2.pin', 'met2.drawing', 'met2.net', 'met2.probe',
    'via2.net', 'via2.drawing', 'via2.boundary', 'met2.psa1', 'met2.psa2', 'met2.psa3', 'met2.psa4', 'met2.psa5',
    'met2.psa6', 'met3.boundary', 'met3.label', 'met3.blockage', 'met3.short', 'met3.pin', 'met3.drawing', 'met3.net',
    'met3.probe', 'via3.net', 'via3.drawing', 'via3.boundary', 'met3.psa1', 'met3.psa2', 'met3.psa3', 'met3.psa4',
    'met3.psa5', 'met3.psa6', 'met4.boundary', 'met4.label', 'met4.blockage', 'met4.short', 'met4.pin', 'met4.drawing',
    'met4.net', 'met4.probe', 'via4.net', 'via4.drawing', 'via4.boundary', 'met4.psa1', 'met4.psa2', 'met4.psa3',
    'met4.psa4', 'met4.psa5', 'met4.psa6', 'met5.boundary', 'met5.label', 'met5.blockage', 'met5.short', 'met5.pin',
    'met5.drawing', 'met5.net', 'met5.probe', 'met5.psa1', 'met5.psa2', 'met5.psa3', 'met5.psa4', 'met5.psa5', 'met5.psa6',
    'rdl.label', 'rdl.res', 'rdl.cut', 'rdl.pin', 'rdl.drawing', 'vhvi.drawing', 'rdl.psa1', 'rdl.psa2', 'rdl.psa3',
    'rdl.psa4', 'rdl.psa5', 'rdl.psa6', 'hvi.drawing', 'pad.label', 'pad.pin', 'pad.drawing', 'target.drawing',
    'pmm2.drawing', 'hvtp.drawing', 'tunm.drawing', 'areaid.seal', 'areaid.core', 'areaid.frame', 'areaid.standardc',
    'areaid.sigPadDiff', 'areaid.sigPadWell', 'areaid.sigPadMetNtr', 'areaid.moduleCut', 'areaid.dieCut',
    'areaid.frameRect', 'areaid.waffleWindow', 'areaid.lowTapDensity', 'areaid.notCritSide', 'areaid.injection',
    'areaid.esd', 'padCenter.drawing', 'areaid.diode', 'areaid.rdlprobepad', 'areaid.deadZon', 'areaid.critCorner',
    'areaid.critSid', 'areaid.substrateCut', 'areaid.opcDrop', 'areaid.extendedDrain', 'areaid.lvNative', 'areaid.hvnwell',
    'areaid.analog', 'areaid.photo', 'areaid.etest', 'areaid.rfdiode', 'npn.label', 'npn.drawing', 'inductor.drawing',
    'inductor.label', 'inductor.term1', 'inductor.term2', 'inductor.term3', 'pnp.drawing', 'pnp.label', 'capacitor.drawing',
    'nwell.net', 'prune.drawing', 'pmm.drawing', 'rpm.drawing', 'conom.maskDrop', 'conom.maskAdd', 'conom.drawing',
    'conom.mask', 'capm.drawing', 'overlap.boundary', 'overlap.drawing', 'cpmm.drawing', 'ncm.drawing', 'nsdm.drawing',
    'psdm.drawing', 'npc.drawing', 'crpm.mask', 'ctunm.drawing', 'ctunm.maskAdd', 'ctunm.maskDrop', 'cncm.drawing',
    'chvtpm.mask', 'capm2.drawing', 'cpbo.mask', 'cmm2.waffleDrop', 'clicm1.maskDrop', 'clicm1.maskAdd', 'cmm3.waffleDrop',
    'cdnm.drawing', 'cdnm.maskAdd', 'cdnm.maskDrop', 'cmm4.waffleDrop', 'cmm4.maskDrop', 'cmm4.maskAdd', 'cli1m.maskDrop',
    'cli1m.maskAdd', 'cmm5.waffleDrop', 'pwell.pin', 'hvntm.drawing', 'lvtn.drawing', 'ubm.drawing', 'bump.drawing',
    'prBoundary.boundary',
    (10, 0), (11, 20), (18, 20), (22, 23), (23, 28), (25, 42), (25, 43), (25, 44), (26, 21), (26, 22), (28, 28), (33, 44),
    (34, 28), (36, 28), (38, 21), (38, 22), (41, 28), (44, 42), (44, 43), (45, 21), (45, 22), (51, 28), (56, 28), (59, 28),
    (62, 20), (62, 21), (62, 22), (65, 4), (65, 5), (65, 6), (65, 16), (65, 23), (65, 41), (65, 48), (65, 60), (66, 58),
    (67, 13), (67, 14), (67, 48), (68, 13), (68, 14), (68, 32), (68, 33), (68, 34), (68, 35), (68, 36), (68, 37), (68, 38),
    (68, 39), (68, 48), (68, 58), (69, 13), (69, 14), (69, 32), (69, 33), (69, 34), (69, 35), (69, 36), (69, 37), (69, 38),
    (69, 39), (69, 48), (69, 58), (70, 13), (70, 14), (70, 17), (70, 32), (70, 33), (70, 34), (70, 35), (70, 36), (70, 37),
    (70, 38), (70, 39), (70, 48), (71, 13), (71, 14), (71, 17), (71, 32), (71, 33), (71, 34), (71, 35), (71, 36), (71, 37),
    (71, 38), (71, 39), (71, 48), (72, 13), (72, 14), (72, 17), (72, 32), (72, 33), (72, 34), (72, 35), (72, 36), (72, 37),
    (72, 38), (72, 39), (74, 15), (74, 22), (79, 20), (83, 44), (88, 44), (89, 32), (89, 33), (89, 34), (89, 35), (89, 36),
    (89, 37), (89, 38), (89, 39), (93, 0), (94, 0), (97, 42), (97, 43), (98, 0), (98, 42), (98, 43), (98, 44), (100, 0),
    (101, 0), (101, 42), (101, 43), (101, 44), (104, 42), (104, 43), (104, 44), (105, 20), (105, 21), (105, 22), (105, 42),
    (105, 43), (105, 44), (106, 44), (107, 20), (107, 21), (107, 22), (108, 20), (108, 21), (108, 22), (109, 42), (109, 43),
    (109, 44), (112, 20), (112, 21), (112, 22), (115, 44), (117, 20), (117, 21), (117, 22), (122, 5), (124, 40), (201, 20),
    (235, 0), (235, 250), (235, 252), (236, 0),
]

valid_layers_ihp_sg13g2 = [
    "Substrate.drawing", "Substrate.text", "Activ.drawing", "Activ.label", "Activ.pin", "GatPoly.drawing", "GatPoly.label",
    "GatPoly.pin", "PolyRes.drawing", "PolyRes.label", "PolyRes.pin", "NWell.drawing", "NWell.label", "NWell.pin",
    "nBuLay.drawing", "nBuLay.label", "nBuLay.pin", "nBuLay.block", "PWell.block", "pSD.drawing", "nSD.drawing",
    "nSD.block", "SalBlock.drawing", "ThickGateOx.drawing", "Cont.drawing", "Metal1.drawing", "Metal1.label", "Metal1.pin",
    "Metal1.text", "Metal1.res", "Via1.drawing", "Metal2.drawing", "Metal2.label", "Metal2.pin", "Metal2.text",
    "Metal2.res", "Via2.drawing", "Via2.net", "Via2.boundary", "Metal3.drawing", "Metal3.label", "Metal3.pin",
    "Metal3.text", "Metal3.res", "MIM.drawing", "Vmim.drawing", "Via3.drawing", "Metal4.drawing", "Metal4.label",
    "Metal4.pin", "Metal4.text", "Metal4.res", "Via4.drawing", "Metal5.drawing", "Metal5.label", "Metal5.pin",
    "Metal5.text", "Metal5.res", "TopVia1.drawing", "TopMetal1.drawing", "TopMetal1.label", "TopMetal1.pin",
    "TopMetal1.text", "TopMetal1.res", "IND.drawing", "IND.pin", "IND.boundary", "IND.text", "TEXT.drawing",
    "Recog.drawing", "Recog.pin", "Recog.esd", "Recog.diode", "Recog.tsv", "Recog.pdiode", "Recog.mom", "DigiBnd.drawing",
    "DigiBnd.drawing0", "RES.drawing", "RES.label", "SRAM.drawing", "SRAM.label", "SRAM.boundary", "DigiSub.drawing",
    "HeatRes.drawing", "NoRCX.drawing", "NoRCX.m2m3", "NoRCX.m2m4", "NoRCX.m2m5", "NoRCX.m2tm1", "NoRCX.m2tm2",
    "NoRCX.m3m4", "NoRCX.m3m5", "NoRCX.m3tm1", "NoRCX.m3tm2", "NoRCX.m4m5", "NoRCX.m4tm1", "NoRCX.m4tm2", "NoRCX.m5tm1",
    "NoRCX.m5tm2", "NoRCX.tm1tm2", "NoRCX.m1sub", "NoRCX.m2sub", "NoRCX.m3sub", "NoRCX.m4sub", "NoRCX.m5sub",
    "NoRCX.tm1sub", "Varicap.drawing", "EXTBlock.drawing", "prBoundary.drawing", "prBoundary.label", "prBoundary.boundary",
    "isoNWell.drawing",
]

valid_layers_gf180mcuD = [
    'PR_bndry', 'pass_mk', 'fail_mk', 'polygon_mk', 'NAT', 'violation_mk', 'MCELL_FEOL_MK', 'MVPSD', 'rule_txt_mk',
    'DNWELL', 'PROBE_MK', 'case_txt_mk', 'Nwell', 'COMP', 'COMP_Dummy', 'COMP_Label', 'ESD', 'ESD_MK', 'Poly2',
    'Poly2_Dummy', 'Poly2_Label', 'Pplus', 'Nplus', 'Contact', 'Metal1', 'Metal1_Slot', 'Metal1_Dummy', 'Metal1_BLK',
    'Metal1_Label', 'Via1', 'Metal2', 'Metal2_Slot', 'Metal2_Dummy', 'Metal2_BLK', 'Metal2_Label', 'Pad', 'Via2', 'Via3',
    'Via4', 'Metal3', 'Metal3_Slot', 'Metal3_Dummy', 'Metal3_BLK', 'Metal3_Label', 'Metal4', 'Metal4_Slot', 'Metal4_Dummy',
    'Metal4_BLK', 'Metal4_Label', 'SAB', 'MetalTop', 'MetalTop_Slot', 'MetalTop_Dummy', 'MetalT_BLK', 'MetalTop_Label',
    'Dualgate', 'Resistor', 'Border', 'FuseTop', 'EFUSE_MK', 'Metal5', 'Metal5_Slot', 'Metal5_Dummy', 'Metal5_BLK',
    'Metal5_Label', 'Via5', 'YMTP_MK', 'NEO_EE_MK', 'FuseWindow_D', 'LVS_RF', 'LVS_Drain', 'LVS_Source', 'SramCore',
    'RES_MK', 'Metal1_Res', 'Metal2_Res', 'Metal3_Res', 'Metal4_Res', 'Metal5_Res', 'Metal6_Res', 'NDMY', 'V5_XTOR',
    'DIODE_MK', 'MDIODE', 'CAP_MK', 'MIM_L_MK', 'LVS_BJT', 'LVS_IO', 'MTPMARK', 'HVPOLYRS', 'OPC_drc', 'PLFUSE', 'DRC_BJT',
    'DEV_WF_MK', 'Latchup_MK', 'IND_MK', 'PMNDMY', 'WELL_DIODE_MK', 'MOS_CAP_MK', 'GUARD_RING_MK', 'OTP_MK', 'ZENER',
    'UBMPPeri', 'UBMPArray', 'UBMEPlate', 'LVPWELL', 'MVSD', 'POLYFUSE', 'LDMOS_XTOR', 'FHRES', 'Schottky_diode',
    (1, 222), (5, 222), (12, 222), (14, 222), (15, 222), (21, 10), (63, 63), (204, 10),
]
# fmt: on

# layers used for the analog pin check
layer_map_sky130A = {
    "met4": (71, 20),
    "via3": (70, 44),
}


def analog_pin_pos_sky130A(pin_number: int, uses_3v3: bool):
    return 151.81 - 19.32 * pin_number - (15.64 if uses_3v3 else 0)


valid_layers = {
    "sky130A": valid_layers_sky130A,
    "ihp-sg13g2": valid_layers_ihp_sg13g2,
    "gf180mcuD": valid_layers_gf180mcuD,
}
layer_map = {"sky130A": layer_map_sky130A}
analog_pin_pos = {"sky130A": analog_pin_pos_sky130A}
lyp_filename = {
    "sky130A": "sky130A.lyp",
    "ihp-sg13g2": "sg13g2.lyp",
    "gf180mcuD": "gf180mcu.lyp",
}

# TODO: read layer numbers from lyp file
valid_lef_port_layers = {
    "sky130A": {
        "met1.pin": (68, 16),
        "met2.pin": (69, 16),
        "met3.pin": (70, 16),
        "met4.pin": (71, 16),
    },
    "ihp-sg13g2": {
        "Metal1.pin": (8, 2),
        "Metal2.pin": (10, 2),
        "Metal3.pin": (30, 2),
        "Metal4.pin": (50, 2),
        "Metal5.pin": (67, 2),
        "TopMetal1.pin": (126, 2),
    },
}
forbidden_layers = {
    "sky130A": [
        "met5.drawing",
        "met5.pin",
        "met5.label",
    ],
    "ihp-sg13g2": [
        "TopMetal2.drawing",
        "TopMetal2.pin",
        "TopMetal2.label",
    ],
    "gf180mcuD": [
        "Metal5",
        "Metal5_Label",
    ],
}
power_pins_layer = {
    "sky130A": "met4",
    "ihp-sg13g2": "TopMetal1",
    "gf180mcuD": "Metal4",
}
power_pins_min_width = {
    "sky130A": 1200,  # 1.2 um
    "ihp-sg13g2": 2100,  # 2.1 um
    "gf180mcuD": 1200,  # 1.2 um
}
boundary_layer = {
    "sky130A": "prBoundary.boundary",
    "ihp-sg13g2": "prBoundary.boundary",
    "gf180mcuD": "PR_bndry",
}

tech_names = ["sky130A", "ihp-sg13g2", "gf180mcuD"]
