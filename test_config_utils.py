from config_utils import override_config


class TestOverrideConfig:
    def test_deprecated_names_of_overrides_are_removed(self):
        config = override_config(
            {"FP_PDN_VPITCH": 38.87, "DESIGN_IS_CORE": 0, "FP_PDN_LOWER_LAYER": "met4"},
            {"PDN_VPITCH": 61.18, "PDN_MULTILAYER": True, "PDN_VERTICAL_LAYER": "met2"},
        )
        assert config == {
            "PDN_VPITCH": 61.18,
            "PDN_MULTILAYER": True,
            "PDN_VERTICAL_LAYER": "met2",
        }

    def test_other_deprecated_names_are_kept(self):
        config = override_config(
            {"FP_PDN_VPITCH": 38.87, "RT_MAX_LAYER": "met4"}, {"RT_MAX_LAYER": "met3"}
        )
        assert config == {"FP_PDN_VPITCH": 38.87, "RT_MAX_LAYER": "met3"}
