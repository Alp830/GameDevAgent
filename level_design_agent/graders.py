import google.generativeai as genai
import re


def RewardsRule(game_levels: str) -> float:
    # Use LLM to analyze the game_levels and return a score based on how well the difficulty increases progressively
    prompt = """
    You are an expert game designer specialized in rewards in game levels. If the level is harder, the reward should NOT be something that makes the levels easier, it should be a something that unlocks harder levels/sections or it can be a cool cosmetic that the player feels proud when they see it (these do the same pyschology as something like a throphy, you don't get any money but you do get a lot of pride). 
    If the level is easier, than the reward should help make the next levels easier in some way.
    If there is no reward do not return anything, otherwise return a score of 1-10, where 1 is poor and 10 is excellent."""
    
    prompt += f"\n\nGame Levels:\n{game_levels}\n\nScore:"
    
    try:
        # Use gemini-2.5-flash (same as your main agent)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate response
        response = model.generate_content(prompt)
        llm_response = response.text.strip()
        
        print(f"LLM response: {llm_response}")  # Debug output
        
        # Extract numeric score from response
        # Handle cases where LLM might return extra text
        score_match = re.search(r'(\d+(?:\.\d+)?)', llm_response)
        if score_match:
            score = float(score_match.group(1))
            # Ensure score is within valid range
            return max(1.0, min(10.0, score))
        else:
            print(f"Could not parse score from LLM response: {llm_response}")
            return 5.0  # Default middle score
            
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return 5.0  # Default middle score if LLM call fails

def multiplePathsRule(game_levels: str) -> float:
    # Use LLM to analyze the game_levels and return a score based on how well the difficulty increases progressively
    prompt = """
    You are an expert game designer specialized in seeing the paths of game levels. Try to see if the model is giving the user ideas of how they can have multiple paths to complete the level.
    Evaluate the difficulty of each pathway that is given and check if there is enough variety between the different paths. Score 1 - 10, where 1 is poor and 10 is excellent.
    Please respond with only a numeric score (e.g., 7.5) without any additional text."""
    
    prompt += f"\n\nGame Levels:\n{game_levels}\n\nScore:"
    
    try:
        # Use gemini-2.5-flash (same as your main agent)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate response
        response = model.generate_content(prompt)
        llm_response = response.text.strip()
        
        print(f"LLM response: {llm_response}")  # Debug output
        
        # Extract numeric score from response
        # Handle cases where LLM might return extra text
        score_match = re.search(r'(\d+(?:\.\d+)?)', llm_response)
        if score_match:
            score = float(score_match.group(1))
            # Ensure score is within valid range
            return max(1.0, min(10.0, score))
        else:
            print(f"Could not parse score from LLM response: {llm_response}")
            return 5.0  # Default middle score
            
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return 5.0  # Default middle score if LLM call fails


# Level Difficulty value Increase Progressively
def score_difficulty_increase_rule(game_levels: str) -> float:
    # Use LLM to analyze the game_levels and return a score based on how well the difficulty increases progressively
    prompt = """
    You are an expert game designer. Analyze the following game levels and score how well the difficulty increases 
    progressively from 1 to 10, where 1 is poor and 10 is excellent.
    
    Please respond with only a numeric score (e.g., 7.5) without any additional text. make sure the difficulty increases around 1-0.5 or more points between levels, an increase of 4-5 may be a little too much"""
    
    prompt += f"\n\nGame Levels:\n{game_levels}\n\nScore:"
    
    try:
        # Use gemini-2.5-flash (same as your main agent)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate response
        response = model.generate_content(prompt)
        llm_response = response.text.strip()
        
        print(f"LLM response: {llm_response}")  # Debug output
        
        # Extract numeric score from response
        # Handle cases where LLM might return extra text
        score_match = re.search(r'(\d+(?:\.\d+)?)', llm_response)
        if score_match:
            score = float(score_match.group(1))
            # Ensure score is within valid range
            return max(1.0, min(10.0, score))
        else:
            print(f"Could not parse score from LLM response: {llm_response}")
            return 5.0  # Default middle score
            
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return 5.0  # Default middle score if LLM call fails
