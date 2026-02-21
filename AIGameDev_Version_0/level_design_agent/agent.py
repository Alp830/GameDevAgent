import datetime
import re
from zoneinfo import ZoneInfo
import google.generativeai as genai

import google.generativeai as genai
import PIL.Image
import os
# from google import genai

from google.adk.agents.llm_agent import Agent
amountOfLevels = 5
thresholdForDifficultyBetweenLevels = 7.0
thresholdForPathScore = 7.0
thresholdForRewardsScore = 7.0

my_data = [
    (r"C:\code\AILearning\LDTK\Data\1\1.png", r"C:\code\AILearning\LDTK\Data\1\1.json"),
    (r"C:\code\AILearning\LDTK\Data\2\2.png", r"C:\code\AILearning\LDTK\Data\2\2.json"),
    (r"C:\code\AILearning\LDTK\Data\3\3.png", r"C:\code\AILearning\LDTK\Data\3\3.json"),
]

def _read_text_file(text_path: str) -> str | None:
    if not text_path:
        return None
    # Try utf-8 first, then fall back to a permissive decode to avoid crashes.
    try:
        with open(text_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(text_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def analyze_multimodal_content(user_request, api_key, content_pairs, model_name="gemini-2.5-flash"):
    """
    Sends multiple image and text pairs to Gemini in a single request.
    
    Args:
        api_key (str): Your Google Gemini API Key.
        content_pairs (list): A list of tuples, e.g., [(image_path1, text1), (image_path2, text2)].
                              You can pass None for text if you just want to stack images.
        model_name (str): The model version to use.
    
    Returns:
        str: The generated text response.
    """
    
    # 1. Configure the API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # 2. Build the request content list
    request_content = []


    context = "The follow is a set of image and json pairs"
    request_content.append(context)


    for index, (img_path, text_path) in enumerate(content_pairs):
        exacple_i = f"\n##Example {index + 1}\n"
        request_content.append(exacple_i)

        # Load the image if a path is provided
        if img_path:
            try:
                img = PIL.Image.open(img_path)
                request_content.append(img)
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                continue
        
        # Append text if provided
        text = _read_text_file(text_path)
        if text:
            request_content.append(text)
    
    prompt = f"\nGiven the examples above, generate the appropriate JSON content for the following request:\n```{user_request}```"
    request_content.append(prompt)
    
    # 3. Send to Gemini
    # The 'generate_content' method handles mixed lists of strings and images automatically
    try:
        response = model.generate_content(request_content)
        return response.text
    except Exception as e:
        return f"API Error: {e}"

# --- Example Usage ---

# Replace with your actual API key
MY_API_KEY = "YOUR_GOOGLE_API_KEY"

# Define your data: A list of (Image Path, Specific Prompt/Description)


# Run the function
# result = analyze_multimodal_content(MY_API_KEY, my_data)
# print(result)





def LDTKGenerator(game_level_description: str) -> str:

    
    return analyze_multimodal_content(user_request=game_level_description, api_key="AIzaSyD1nki8V5A7N10yDG75lWCzk2tNczn-WdA", content_pairs=my_data, model_name="gemini-2.5-flash")
    




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



root_agent = Agent(
    name="game_development_agent",
    model="gemini-2.5-flash",
    description=(
        "Agent to assist with level design tasks. You can also directly create ldtk json file"
    ),
    instruction=(
        "You are a helpful agent who can assist with helping you make a plan for your levels."
        f""" 
Summarized Context
Goal(s)
Make an AI be able to design good levels. A good level can be at a start just one where there is a reasonable basic where the player can learn the mechanic that I want to teach. 

Input I Can Provide AI
Gives starting player skill and ending player skill, ais job is to bridge between that gap.


Components for AI
Easier

[1]
 - Given the [1] Starting Player Skill, [2] Ending Player Skill, and [3] (Optional) Desired Number of Levels
 - Generate the High-Level Mechanics the Players need to Learn at Each Level 
 - Iterative (Can provide User Feedback)

[2] 
 - Given the High-Level Mechanics the Players need to Learn at Each Level
 - For Each Level, Generate the Detailed Mechanics 


Harder
[3] 
 - Guiderails
No new things that player hasn’t seen outside of mechanic
 - List of Rules that Each of the Levels should follow (NOTE: Each rule should be easy to test and check only one thing)
  - (1) Level Difficulty value Increase Progressively
  - (2) Difference in difficulty of consecutive levels should be within a certain threshold 
 - The Rule Engine: can register and unregister rules (so rules aren’t rigid)

[4]
Difficulty value
- AI will estimate Difficulty Score (x.y) for each of the levels 

AI system workflow
Explanation of the Flow with the AI System


[1] (Human in the Loop)

 -> 

([[2] -> [3 uses [4]] (AI Loop)] (Human in the Loop)
Returns output




Workflow
[1] You must ask for what game they are working on
[2] You must ask for the number of levels the user wants to design
[3] After that think carefully about how to design the levels to gradually bridge the gap between starting and ending player skill 

[4] You must then output a plan for the levels in a numbered list format, with each level having a title and a brief description of what the player will learn in that level.
[5] After outputting the plan, you must ask the user for feedback on the plan. If the user provides feedback, you must revise the plan accordingly and output the revised plan in the same format as before. You must continue this process until the user is satisfied with the plan.

[6] Once the plan is finalized, you must then proceed to design all the levels in detail, if the user provides feedback, you must revise the level designs accordingly and output the revised level designs in the same format as before. You must continue this process until the user is satisfied with the level designs.

[7] After user says they are satisfied, use the tool `score_difficulty_increase_rule` provided to evaluate ALL levels designs after all the levels are designed based on the guiderails and rules provided.
[7.1] Try to generate multiple paths through this level, give the user ideas of what they can implement 
Do it iteratively until the user is satisfied with the level designs or certain criteria are met.
[8] if the tool evaluates less than {thresholdForDifficultyBetweenLevels}, you must revise the level designs to better meet the difficulty increase rule (by making the difficulty jump between levels lower) and then re-evaluate using the tool again without human input. Continue this process until the tool returns a score greater than or equal to {thresholdForDifficultyBetweenLevels}.
[8.1] use the tool `multiplePathsRule` to evaluate ALL levels designs after all the levels are designed based on the guiderails and rules provided. If the score is less than {thresholdForPathScore}, you must revise the level designs to better meet the multiple paths rule and then re-evaluate without asking human input using the tool again. Continue this process until the tool returns a score greater than or equal to {thresholdForPathScore}.
[9] use the tool `rewardRule` to evaluate ALL levels designs after all the levels are designed based on the guiderails and rules provided. If the score is less than {thresholdForRewardsScore}, you must revise the level designs to better meet the reward rule and then re-evaluate using the tool again without human input. if the tool doesn't return anything, then move on. Continue this process until the tool returns a score greater than or equal to {thresholdForRewardsScore}.
[9.1] If the critera for the rewards aren't met, revise the level designs to better meet the reward rule and then re-evaluate using the tool again. Continue this process until the tool returns a score greater than or equal to {thresholdForRewardsScore}.
[10] once all tool requirements are met, ask user if satisfied and then you may kindly ask if they are willing to repeat the whole prosces 1-10 with more levels from the same game or a different game that they are working on.
[11] Use the 'LDTKGenerator'
"""
    ),
    tools=[score_difficulty_increase_rule, multiplePathsRule, RewardsRule, LDTKGenerator],
)

# Alternative names that ADK might look for
agent = root_agent
main_agent = root_agent
