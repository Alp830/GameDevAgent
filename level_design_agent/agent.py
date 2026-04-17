
from google.adk.agents.llm_agent import Agent
amountOfLevels = 5
thresholdForDifficultyBetweenLevels = 7.0
thresholdForPathScore = 7.0
thresholdForRewardsScore = 7.0
API_KEY="AIzaSyDa8oGtpSEUCAcwqN9f8oTt0Jy_zin5-Og"
try:
    from . import converters as conv
    from . import graders as grd
except ImportError:
    import converters as conv
    import graders as grd



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
[9.1] If the critera for the rewards aren't met, revise the level designs to better meet the reward rule and then re-evaluate using the tool again. Continue this process until the tool returns a score greater than or equal to {thresholdForRewardsScore}. (you need to try making more skillfull levels open more challenging sections and less skillful levels help add assist options)
[10] once all tool requirements are met, ask user if satisfied and then you may continue, ask user whether they want AgentLangauge converter tools to be userd
[11] Use the `AgentLanguageConverter` 
[12] After converting, give AgentLanguageConverter data and ask if they want Bridge tool to be used
[13] Use the `BridgeDataConverter` to convert the data into a format that can be used to create ldtk json files. After converting, ask user if they want to create ldtk json files using the converted data.
[14] If user says yes, use the `LDTKGenerator` tool to create ldtk json files using the converted data. After creating, ask user if they want to make any revisions to the ldtk json files.
[15] If user wants to make revisions, make the revisions and then re-evaluate using the tools again without asking human input. Continue this process until all tool requirements are met and user is satisfied with the final level designs and ldtk json files.
"""
    ),
    tools=[grd.score_difficulty_increase_rule, grd.multiplePathsRule, grd.RewardsRule, conv.LDTKGenerator, conv.AgentLanguageConverter, conv.BridgeDataConverter],
)

# Alternative names that ADK might look for
agent = root_agent
main_agent = root_agent
