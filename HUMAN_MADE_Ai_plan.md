_D3. Heuristic coach / "question-judging" trainer._*

The user will be given Physics GRE problems (for now we'll use real problems, we can work on generation later), and asked to write in words how they would solve it on the exam

- Note: We should not rush the student at this point, as we want them to give a sufficent explanation

From there, (if AI is on), the AI will see not just if the answer is correct, but also if the solution was optimal

Examples of unoptimal solutions might be

- A student not crossing off an obviously wrong answer (Ex: A speed faster than light)
- A student not usiing numerical estimates when the answer choices are not near to eachother (Ex: 10^0, 10^2, 10^5, 10^8, 10^11)
- Any other situation where the student fully solved a problem that wasn't fully solveable
- Pure guesswork ("E just seemed right"). There should be an actual POE, not just vibes (In case it's not obvious, short answer doesn't always mean optimal)

Importanly, this does not mean that the student always needs tricks. In some problems, the optimal solution is to just fully solve it as if it was a Free response exam

- You can use the tricks in "Conquering the Physics GRE" and see if any can reasonably apply, as well as concepts seen in the brainlift

Stage 1: Eval
Using the scraped problems, solutions, explanations, and techniques in the GRE textbook, come up with prompts for GPT-4o (API Key to be given) toi give the "optimal" solutions for the problems. Then check against the standards listed above (did GPT use optimal tricks, did it do something incorrect, etc). Go thru several rounds of prompting and checking until GPT-4o gives satsifying explanations for all of the problems (Note: For any problems with listed solutions, compare them to see if GPT-4o gives an equal or better response than the student-made one)
