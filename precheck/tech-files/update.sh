#!/bin/sh

curl -L -O https://github.com/efabless/mpw_precheck/raw/main/checks/tech-files/sky130A_mr.drc
curl -L -O https://github.com/efabless/mpw_precheck/raw/main/checks/drc_checks/klayout/zeroarea.rb.drc
curl -L -O https://github.com/efabless/mpw_precheck/raw/main/checks/drc_checks/klayout/pin_label_purposes_overlapping_drawing.rb.drc

echo "Don't forget to update the revision numbers in README.txt"
