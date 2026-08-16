import pytest

from ingest.metadata import ManualMeta, enrich_from_pdf, from_filename


@pytest.mark.parametrize(
    "filename,model,language,os_version",
    [
        ("SAM_S911_S916_S918_EN_UM_OS13_030223.pdf", "Galaxy S23 series", "en", "Android 13"),
        ("SM-S928U_UM_EN_OS14.pdf", "Galaxy S24 Ultra", "en", "Android 14"),
        ("SM-S921B_UM_EN.pdf", "Galaxy S24", "en", None),
        ("galaxy-s24-ultra_en_um.pdf", "Galaxy S24 Ultra", "en", None),
        ("SM-F956B_UM_EN_OS14.pdf", "Galaxy Z Fold6", "en", "Android 14"),
        ("SM-F741U_UM_EN.pdf", "Galaxy Z Flip6", "en", None),
        ("SM-A556E_UM_ES.pdf", "Galaxy A55 5G", "es", None),
        ("SM-S938U_UM_EN_OneUI7.pdf", "Galaxy S25 Ultra", "en", "One UI 7"),
    ],
)
def test_parses_real_world_filenames(filename, model, language, os_version):
    meta = from_filename(filename)
    assert meta.model == model
    assert meta.language == language
    assert meta.os_version == os_version


@pytest.mark.parametrize(
    "codes,expected",
    [
        (["SM-S928W"], "Galaxy S24 Ultra"),
        (["SM-S921W", "SM-S926W", "SM-S928W"], "Galaxy S24 series"),
        # The real case that made this necessary: one file, two generations.
        (
            ["SM-S921W", "SM-S928W", "SM-S931W", "SM-S938W"],
            "Galaxy S24/S25 series",
        ),
        (["SM-F946W", "SM-F956W"], "Galaxy Z Fold5/Z Fold6 series"),
    ],
)
def test_display_model_describes_the_whole_family(codes, expected):
    from ingest.metadata import display_model

    assert display_model(codes) == expected


def test_display_model_does_not_invent_names_for_unknown_codes():
    """A guessed marketing name would be printed under every citation."""
    from ingest.metadata import display_model

    assert display_model(["SM-S942W", "SM-S947W"]) == "Galaxy S942/S947"
    assert display_model(["SM-S938W", "SM-S942W"]) == "Galaxy S25 Ultra (+S942)"


def test_region_extracted_when_present():
    assert from_filename("SM-S928U_UM_EN_US.pdf").region == "US"
    assert from_filename("SM-S928B_UM_EN.pdf").region is None


def test_unknown_model_is_empty_not_wrong():
    """Better to record nothing than to guess a model the citation will show."""
    meta = from_filename("mystery_manual.pdf")
    assert meta.model == ""
    assert meta.language == "unknown"


def test_language_filter_flag():
    assert from_filename("SM-S928U_UM_EN.pdf").is_english
    assert not from_filename("SM-S928U_UM_KO.pdf").is_english


def test_multi_model_manual_named_as_family():
    """S911/S916/S918 is one manual for three phones; calling it "Galaxy S23"
    alone would mislabel every citation from it."""
    meta = from_filename("SAM_S911_S916_S918_EN_UM.pdf")
    assert meta.model == "Galaxy S23 series"
    assert meta.model_codes == ["S911", "S916", "S918"]


def test_enrich_fills_model_from_pdf_when_filename_is_useless():
    meta = from_filename("download.pdf")
    assert meta.model == ""
    enriched = enrich_from_pdf(
        meta,
        {"title": "Galaxy S24 Ultra User Manual"},
        first_page_text="SM-S928U User Manual",
    )
    assert enriched.model == "Galaxy S24 Ultra"


def test_enrich_ignores_boilerplate_pdf_titles():
    meta = ManualMeta(model="Galaxy S24", model_codes=["S921"], language="en")
    enriched = enrich_from_pdf(meta, {"title": "Microsoft Word - UM.doc"}, "")
    assert enriched.title == "Galaxy S24 User Manual"


def test_enrich_does_not_override_filename_model():
    meta = from_filename("SM-S928U_UM_EN.pdf")
    enriched = enrich_from_pdf(meta, {"title": "Galaxy S23 User Manual"}, "SM-S918B")
    assert enriched.model == "Galaxy S24 Ultra"
