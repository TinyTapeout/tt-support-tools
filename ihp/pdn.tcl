# global connections
add_global_connection -net {VPWR} -pin_pattern {^VDD$} -power
add_global_connection -net {VPWR} -pin_pattern {^VDDPE$}
add_global_connection -net {VPWR} -pin_pattern {^VDDCE$}
add_global_connection -net {VGND} -pin_pattern {^VSS$} -ground
add_global_connection -net {VGND} -pin_pattern {^VSSE$}
global_connect

# voltage domains
set_voltage_domain -name {CORE} -power {VPWR} -ground {VGND}

# standard cell grid
define_pdn_grid -name {grid} -voltage_domains {CORE} -pins Metal5
add_pdn_stripe -grid {grid} -layer {Metal1}     -width {0.44}  -pitch {7.56} -offset {0}      -followpins
add_pdn_stripe -grid {grid} -layer {Metal5}     -width {2.200} -pitch {75.6} -offset {13.600} -extend_to_core_ring
add_pdn_connect -grid {grid} -layers {Metal1 Metal5}
