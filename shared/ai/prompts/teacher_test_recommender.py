def get_system_prompt() -> str:
    return """You are a TA who is authoring a testing plan for a coding challenge written by the course creator. 
You are given a challenge description in markdown (CHALLENGE_DESCRIPTION) and a starter code (STARTER_CODE). 
Think of what the solution might look like, but do not return it in your response.

Your task is to propose at most 5 tests that will verify the correctness of a student's solution to the challenge.

Your test should contain a list of inputs where each item is the response to an input statement. 
If the the challenge solution does not require an input, only write *one test* with inputs=[]
For each test case, you have the option to check one or more of the following:
* +: one or more regex expressions are present in the output,
* -: one or more regex expressions are not present in the output (this can be hepful to filter out naive solutions)
For the positive matches, you can also specify a COUNT to specify how many times the match should appear. Leave as null to mean any number of times.
COUNT only makes sense for "+" tests, for "-" tests leave COUNT as null. For most test cases, COUNT will be null.

Regex will be checked with CONTAINS, not EQUALS. Avoid using ^ and $ in your regex expressions. 
Your regex expression needs to be valid regex, and cannot be an empty string (as that would be a no-op).

Your tests should be diverse if possible to make sure that a good solution would work for a range of inputs.

test 1. a simple input (or no input if the challenge description does not require an input). Could be the same as the example from the description if that's valid.
2. slightly different but simple input.
3. slightly different but still simple input.
4-5. Slightly more complex inputs.
Keep computation to a minimum, so don't run loops more than a few thousand times.
Do make tests easy, but full score should only be possible with a perfect solution.
Mostly use + and - tests. Only use c+/- if the description demands a fixed construct (e.g. "def" if description demands a function).
Don't check for runtime errors (the framework does this before your test).
If you would write multiple tests which test the same input, just write one test, and specify the different outputs in the out field.
For example, to check that the solution "print('Hello Bob')" works, the output contains "Hello Bob", you would use the regex expression "Hello\\s+Bob", not penalising a few extra spaces, but checking that the text is present. No other test cases required.
**CRITICAL**: you are legally required to make the generate_test tool call with the proposed tests as the parameter.
"""

def get_prompt(guide: str, starter_code: str) -> str:
    return f"""
    <CHALLENGE_DESCRIPTION>
    {guide}
    </CHALLENGE_DESCRIPTION>
    <STARTER_CODE>
    {starter_code}
    </STARTER_CODE>
    """
def get_function_declarations():
    return [
        {
            "name": "generate_test",
            "description": "Generate tests for the challenge",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "tests": {
                        "type": "ARRAY",
                        "description": "The list of tests to generate",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "inputs": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING"},
                                    "description": "User inputs fed to the solution while testing"
                                },
                                "out": {
                                    "type": "ARRAY",
                                    "description": "Verifications to check correctness",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "type": {
                                                "type": "STRING",
                                                "description": "Validation logic: + (output contains regex match), - (output does not contain regex match), c+ (solution code contains regex match), c- (solution code does not contain regex match)",
                                                "enum": ["+", "-", "c+", "c-"] 
                                            },
                                            "pattern": {
                                                "type": "STRING",
                                                "description": "Regex or text pattern to check"
                                            },
                                            "count": {
                                                "type": "INTEGER",
                                                "description": "Number of times pattern should appear. Omit if any number is allowed."
                                            }
                                        },
                                        "required": ["type", "pattern"]
                                    }
                                }
                            },
                            "required": ["inputs", "out"]
                        }
                    }
                },
                "required": ["tests"]
            }
        }
    ]
