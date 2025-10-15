from src.utils import parse_price_text

def test_parse_price_basic():
    assert parse_price_text("S/ 549") == 549.0
    assert parse_price_text("S/ 1,299.90") == 1299.90
    assert parse_price_text("S/ 1.299,90") == 1299.90
