rough plan and requirements for this project
# Topic overall: 
- this project is to desig and create a tool using genai agentic apporach (probably) to enahnce the resume enahncemnts.

# Problem
whenever someone wants to apply for a new job, he needs to enhance his resume to make it best for that job.  This usually involves tailoring the resume to highlight the most relevant skills, experiences, and achievements that match the job description, which can be time-consuming and challenging for many applicants. at the sametime we don't want to fabricate the resume. all should be based on the actuall jobs that happens.
## MUST DO:
- the tool should tailor the summery if there is one on the top
- manipulate the sections order
- manipulate the bullet points within each section
- manipulate, enhance and rephrase the skill section
- enhance and rephrase the work experience section to better highlight achievements and responsibilities and also be more relevent to the job
- add or remove sections or reorder them based on what is most relevant to the job description
- be able to collect relevent information from the web and from the job description
- should able to parse a direct link and extract the job description from it
- be able to suggest improvements without changing the factual content of the resume

## The tool shoud not
- fabricate any information that is not true or not present in the original resume
- exaggerate responsibilities or achievements beyond what actually happened
- add skills or experiences that the applicant does not have

# senraio 
supposed that you have someone with several years of experience. he has so many project under his umberella. but we cannot fit all in a resume. also sometimes there are things that we don't know how to fit in into a project. for example, if you have done a independent project, or a research paper, or some consulting work. 
In this situation, the user will provide all the work he has done ever that could be relevent. for example in a comprehensive resume. also a job description will be provided as a simple text or a link to the job posting. then the tool start parsing and one by one go through each piece and enhance it to the best way possible. possibly for the bullet points after the first couple of the bullets you will learn how to do it from his feedback and you can do the rest all together. 
always check the content with the user. 
also after a few job descriptions the tool should be able to infer from the past interactions and give the suggestions in a sigle shot.
The final output of the resume is a ats friendly pdf format. probaly we can have it using Latex formating or html.  but the layout should be professional and astetically pleasunt 
This tool also should be able to provide a nice cover later if needed.
 
# agent design
I like to have the multi-agent having the role play for the resume enhancer. supposed one is an experience recuiter, the hiring manager, and we can have a professional resume writer or any other rule. 

# framework for backedn
I prefere langchain/langgraph/langsmith framework to be used for the agent design.

# frontend 
we can start the prototype using streamlit with full user account managment. but later we want to change it to probably react.js.The frontend should be a chat-based format with enough sections that needed.

# databases
I am open to any database that is suited for this purpose

# design communications
all the frontend, backend, and database should communicate through REST API.

From a UI/UX stand point this should be pleasent 