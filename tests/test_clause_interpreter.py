import pytest
import json

def test_initial_state(direct_deploy):
    # Deploy contract and check initial count is 0
    contract = direct_deploy("contracts/clause_interpreter.py", sdk_version="v0.2.16")
    assert contract.get_total_records() == 0

def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/clause_interpreter.py", sdk_version="v0.2.16")
    
    # Test empty policy_clause
    with pytest.raises(Exception) as excinfo:
        contract.interpret_clause("", "Event description")
    assert "policy_clause must not be empty" in str(excinfo.value)
    
    # Test empty event_description
    with pytest.raises(Exception) as excinfo:
        contract.interpret_clause("Policy clause", "")
    assert "event_description must not be empty" in str(excinfo.value)

def test_interpret_clause_happy_path(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/clause_interpreter.py", sdk_version="v0.2.16")
    
    # Mock LLM verdict
    direct_vm.mock_llm(
        r".*",
        '{"verdict": "APPLIES", "confidence": 98, "reasoning": "A class 12 typhoon warning meets the criteria for extreme weather conditions."}'
    )
    
    # Execute interpretation
    contract.interpret_clause(
        policy_clause="Employees are allowed to be absent in the event of extreme weather causing hazard to travel.",
        event_description="A level 12 typhoon warning issued for the city, and citizens are urged by the government to remain indoors."
    )
    
    assert contract.get_total_records() == 1
    
    # Retrieve and parse record
    record_json = contract.get_record("0")
    record = json.loads(record_json)
    
    assert record["id"] == "0"
    assert record["policy_clause"] == "Employees are allowed to be absent in the event of extreme weather causing hazard to travel."
    assert record["event_description"] == "A level 12 typhoon warning issued for the city, and citizens are urged by the government to remain indoors."
    assert record["verdict"] == "APPLIES"
    assert record["confidence"] == 98
    assert record["reasoning"] == "A class 12 typhoon warning meets the criteria for extreme weather conditions."
