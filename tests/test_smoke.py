requirements.txt:
pytest
@agent

pytest.ini:
[pytest]
addopts = -v

tests/test_smoke.py:
def test_hello_world():
    assert 1 + 1 == 2

def test_application_functionality():
    assert True  # Replace with actual checks for your application