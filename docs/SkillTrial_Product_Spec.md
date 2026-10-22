# Project: SkillTrial — Resume Skill Verification Through Practical Micro-Challenges

> This is the **original, definitive product specification** exactly as provided by the project owner. The implementation plan (`SkillTrial_Implementation_Plan_LLD.md`) is derived from it. If the two ever disagree, the owner's later decisions in `PROJECT_CONTEXT.md` win (for example: the recruiter side is deferred).

## 1. Project Overview

Build a complete, polished, and functional web-based application called **SkillTrial** that enables job applicants to verify the skills mentioned on their resumes through short, practical, time-bound micro-challenges.

The main purpose of SkillTrial is to bridge the gap between what candidates claim to know and what they can actually demonstrate.

Traditional recruitment often relies heavily on resume keywords, self-reported proficiency levels, certificates, and academic qualifications. These indicators do not always provide sufficient evidence of a candidate's practical abilities.

SkillTrial addresses this problem by allowing candidates to upload their resumes, extract their claimed skills, complete relevant assessments, and receive an evidence-backed report explaining which skills have been demonstrated and which require further evaluation or improvement.

The platform must provide more than a conventional quiz or coding assessment website. It should combine practical skill verification, transparent evidence, AI-assisted critical thinking, and personalized skill development into one connected experience.

The application should be designed for job applicants, students preparing for placements, recruiters reviewing candidate profiles, and administrators managing assessments.

## 2. Core Objectives

The application must achieve the following objectives:

1. Extract relevant technical skills and stated proficiency levels from uploaded resumes.
2. Allow candidates to verify their claimed skills through realistic practical tasks.
3. Evaluate performance using objective, skill-specific criteria.
4. Generate transparent reports supported by actual assessment evidence.
5. Identify gaps between claimed proficiency and demonstrated performance.
6. Evaluate a candidate's ability to critically assess AI-generated technical suggestions.
7. Provide personalized, gamified learning paths for improving weak skills.
8. Allow candidates to reassess their skills and track progress over time.
9. Enable candidates to share selected verification results with recruiters while maintaining control over their personal information.
10. Clearly communicate the scope and limitations of every assessment.

## 3. User Roles

### A. Candidate

Candidates should be able to:
- Create and manage their profiles.
- Upload and manage resumes.
- Review skills extracted from their resumes.
- Confirm or correct extracted skill claims.
- Select skills they want to verify.
- Complete practical assessments.
- View evaluation results and supporting evidence.
- Identify strengths and skill gaps.
- Receive personalized practice recommendations.
- Earn learning points, levels, and badges.
- Track progress across repeated assessments.
- Generate and download skill verification reports.
- Create, manage, and revoke report-sharing links.

### B. Recruiter or Report Viewer

Recruiters should be able to:
- Open a candidate's explicitly shared report.
- Review the skills the candidate chose to verify.
- Understand the candidate's claimed proficiency and demonstrated results.
- Inspect the types of challenges completed and the evidence supporting the results.
- Identify competencies that were demonstrated and those that were not adequately assessed.
- Understand the limitations of the report.

Recruiters must not gain access to private resumes, personal information, source code, or assessment history unless the candidate has explicitly authorized the relevant access.

### C. Administrator

Administrators should be able to:
- Manage users and platform settings.
- Create and manage skills and competencies.
- Create and edit assessment challenges.
- Define challenge difficulty and evaluation criteria.
- Configure expected outcomes and test cases.
- Review and approve challenges before publication.
- Manage learning resources and badges.
- Review platform-level usage and assessment statistics.
- Inspect relevant audit records.

Administrative actions must be permission-controlled and recorded where appropriate.

## 4. Resume Upload and Skill Extraction

Build a complete resume-based skill discovery workflow.

### Step 1: Upload a resume

Allow candidates to upload a resume in supported document formats. Display clear file requirements, upload progress, and useful error messages.

Validate uploaded files and handle unreadable, corrupted, unsupported, or empty documents gracefully.

### Step 2: Extract resume information

Analyze the resume to identify:
- Technical skills.
- Programming languages.
- Frameworks and tools.
- Databases.
- Technical domains.
- Explicitly stated proficiency levels.
- Relevant project or experience descriptions that provide context for the claimed skills.

The system must not assume that a skill is advanced merely because it appears frequently or is mentioned in a project.

### Step 3: Normalize skill names

Recognize common aliases and related terms while preserving meaningful distinctions between different skills.

For example, knowledge of Java should not automatically be treated as proof of Spring Boot proficiency.

### Step 4: Candidate confirmation

Display the extracted information in an editable review screen.

For each skill, show:
- Extracted skill name.
- Stated proficiency, if available.
- Relevant resume evidence.
- Extraction confidence.
- Confirmation status.

Allow candidates to correct extraction mistakes, remove irrelevant claims, and add missing skills.

Clearly distinguish between a candidate-confirmed claim and a skill verified through assessment.

### Step 5: Select skills for verification

Let candidates select one or more skills they want to assess.

Prioritize the skills selected by the candidate and those relevant to their stated career goals. Do not force candidates to verify every skill listed on their resume.

## 5. Skill Catalog and Competency Mapping

Create a structured catalog of assessable skills.

Each skill should contain:
- Skill name and description.
- Related competencies.
- Suggested proficiency levels.
- Assessment types suitable for the skill.
- Evaluation criteria.
- Challenge difficulty levels.
- Learning resources.
- Minimum evidence requirements for verification.

For example, the Java skill may include object-oriented programming, collections, exception handling, debugging, algorithmic problem-solving, and code quality.

SQL may include joins, aggregation, subqueries, NULL handling, duplicate records, data filtering, and query correctness.

Spring Boot may include REST API implementation, validation, exception handling, service-layer logic, and database integration.

Do not assume that success in one competency proves mastery of the entire skill.

Assessments should be designed around the competencies actually being evaluated.

## 6. Practical Micro-Challenge System

For each selected skill, provide short, focused, time-bound tasks.

The purpose is to assess practical ability rather than memorization alone.

Support multiple challenge types.

### A. Coding Challenges

Present programming problems with:
- Clear problem statements.
- Input and output specifications.
- Constraints.
- Sample examples.
- Time limits.
- A code-writing interface.
- Submission and execution feedback.

Evaluate correctness against predefined tests, including hidden edge cases, and measure efficiency when the challenge requires it.

### B. SQL Challenges

Provide a small, relevant database scenario with tables, sample records, and a task description.

Ask candidates to write queries that solve realistic data problems.

Evaluate query results against expected outcomes. Include cases involving NULL values, duplicates, joins, aggregation, filtering, and ordering where appropriate.

Use controlled, read-only execution for candidate queries unless a challenge explicitly requires another safely isolated setup.

### C. Debugging Challenges

Provide code containing intentional defects.

Ask candidates to identify the problem, correct it, and demonstrate that the revised implementation behaves as expected.

Evaluate whether the fix addresses the actual defect and preserves previously correct behavior.

### D. Scenario-Based Challenges

Present practical technical situations that require candidates to make decisions and explain their reasoning.

Examples include choosing an appropriate data structure, identifying a database integrity problem, investigating an API failure, or deciding how to handle an edge case.

Evaluate answers using predefined rubrics rather than arbitrary subjective judgments.

### E. Challenge Difficulty

Organize challenges into beginner, intermediate, and advanced levels.

Difficulty should reflect the actual competencies required, not merely the length of the question.

Use a suitable mixture of challenge types and difficulties to gather enough evidence about the selected skill.

## 7. Assessment Workflow

Every assessment must follow a clearly defined process.

1. The candidate selects a skill.
2. The platform explains the assessment format, time limit, and evaluation criteria.
3. The candidate begins the assessment.
4. The platform presents the assigned challenges.
5. The candidate works on each challenge within the permitted time.
6. The candidate submits their responses.
7. The platform evaluates the submissions.
8. The platform records the results and supporting evidence.
9. The candidate receives a detailed assessment report.
10. The platform recommends suitable next steps.

The assessment deadline must be enforced by the system, not merely by a visual countdown.

Handle incomplete assessments, expired sessions, execution errors, and interrupted submissions transparently.

Prevent duplicate submissions from awarding duplicate points or creating inconsistent results.

Do not expose hidden test cases, answer keys, or expected solutions before the assessment is complete.

## 8. Evaluation and Scoring

Evaluate each challenge using criteria appropriate to its type.

Possible criteria include:
- Functional correctness.
- Edge-case handling.
- Time and space efficiency.
- Code quality.
- Debugging accuracy.
- Validity of the candidate's reasoning.
- Ability to test assumptions.
- Recognition of logical or security flaws.

Not every criterion should apply to every task.

Use explicit scoring rubrics and document how the final result is calculated.

For programming challenges, deterministic test execution should be the primary measure of correctness.

For SQL challenges, compare results against expected behavior, including relevant duplicate and NULL cases.

For scenario-based responses and explanations, use predefined evaluation criteria and clearly communicate the limitations of subjective or AI-assisted evaluation.

A single successful challenge must not automatically prove advanced proficiency.

Require sufficient evidence across relevant competencies before assigning a high proficiency level.

## 9. Evidence-Backed Skill Verification Report

After an assessment, generate a comprehensive report for each evaluated skill.

Use exactly four verification statuses.

### Verified

The available evidence is sufficient to meet the defined criteria for the assessed proficiency level.

### Partially Verified

The candidate has demonstrated some relevant competencies but has not met all required criteria.

### Not Verified

Sufficient assessment evidence indicates that the defined criteria were not met.

### Insufficient Evidence

The assessment was incomplete, insufficiently representative, inconclusive, or otherwise unable to support a reliable decision.

Do not use Not Verified as a substitute for an incomplete assessment.

### Report contents

Include:
- Candidate display name.
- Assessment date.
- Skill being evaluated.
- Original claimed proficiency, if stated.
- Candidate-confirmed skill claim.
- Demonstrated proficiency, when supported by sufficient evidence.
- Final verification status.
- Challenges completed.
- Challenge difficulty and types.
- Correctness and relevant performance metrics.
- Competencies demonstrated.
- Competencies requiring improvement.
- Supporting evidence from completed tasks.
- Strengths and weaknesses.
- Suggested next steps.
- Assessment limitations.

Explain why the status was assigned in language candidates and recruiters can understand.

Do not describe the report as a universal professional certification or guarantee of job performance.

### Report access

Allow candidates to:
- View reports on their dashboard.
- Download reports as PDF documents.
- Create shareable report links.
- Choose which reports they share.
- Revoke previously created links.

Shared reports must not expose private resume data or unrelated personal information.

## 10. Distinctive Feature: AI-Assisted Trust Challenges

This is one of the most important features of SkillTrial.

The objective is to assess whether a candidate can critically evaluate AI-generated technical suggestions instead of blindly accepting them.

A candidate must demonstrate the ability to judge code, identify incorrect assumptions, validate suggestions, and explain technical decisions.

### Challenge design

Present a realistic technical task alongside multiple proposed solutions or recommendations.

These may include:
- A correct solution.
- A solution that works for ordinary inputs but fails on an edge case.
- A solution containing a subtle logical defect.
- An inefficient approach.
- A solution with a security or data-integrity problem, where relevant.

Do not label the suggestions as correct or incorrect.

The challenge must contain a clearly defined expected behavior and a reliable method for evaluating the candidate's judgment.

### Candidate workflow

1. Read the technical task.
2. Review the proposed AI-generated suggestions.
3. Select a solution, reject a suggestion, or compare multiple alternatives.
4. Identify the suspected defect or explain why a suggestion is valid.
5. Construct a counterexample when appropriate.
6. Propose or execute a test that validates the claim.
7. Explain the reasoning.
8. Submit the final decision.

### Evaluation

Evaluate:
- Whether the candidate selected or rejected the appropriate suggestion.
- Whether the identified issue is real.
- Whether the counterexample exposes the claimed defect.
- Whether the proposed test validates the relevant behavior.
- Whether the candidate's explanation matches the observed results.
- Whether the candidate recognizes efficiency, reliability, or security concerns when relevant.

Use deterministic tests and predefined answer criteria wherever possible.

AI-assisted evaluation may help interpret explanations, but it must not be the sole authority for correctness.

Every challenge must have validated expected outcomes before publication.

### Example

A candidate receives a Java method that appears to calculate an average.

The proposed AI solution works for ordinary input but fails when the collection is empty.

The candidate must:
- Identify the problematic condition.
- Explain the potential failure.
- Construct an appropriate test.
- Verify the behavior.
- Recommend a correction.
- Confirm that the correction handles the relevant cases.

The system then evaluates the evidence and updates the candidate's AI-assisted technical judgment results.

### Important distinction

Do not claim that this feature detects every instance of AI use, proves code authorship, or establishes that a candidate never relies on AI.

It assesses demonstrated technical judgment in the specific tasks presented.

## 11. Gamified Skill Improvement

When a candidate performs poorly or demonstrates gaps in a skill, provide a structured path for improvement.

Do not stop at displaying a low score.

### Personalized recommendations

Identify the competencies that require improvement and recommend relevant learning material and practice challenges.

For example, if a candidate struggles with SQL joins and duplicate rows, prioritize those topics instead of recommending a generic SQL course.

### Gamification features

Implement:
- XP points.
- Skill levels.
- Achievement badges.
- Practice goals.
- Progress indicators.
- Streaks with clearly defined rules.
- Challenge completion history.
- Milestone achievements.
- Personalized learning paths.
- Reassessment opportunities.

Example badges:
- Java Problem Solver.
- SQL Detective.
- Edge Case Explorer.
- Debugging Specialist.
- AI Trust Analyst.

Award points according to defined completion and performance rules. Prevent duplicate awards from repeated requests.

### Learning and re-verification

After completing a learning activity, candidates should be able to attempt new or appropriately varied challenges.

Compare their new results with previous assessments.

Display improvements and remaining weaknesses honestly.

Keep gamification achievements separate from formal skill verification. Earning a badge must not automatically change a skill's verification status.

## 12. Candidate Dashboard

Create a personalized dashboard that gives candidates a clear overview of their current skill profile.

Display:
- Resume-processing status.
- Extracted and confirmed skills.
- Claimed proficiency levels.
- Verification statuses.
- Skills awaiting assessment.
- Completed assessments.
- Recent results.
- Areas requiring improvement.
- Recommended challenges.
- Current learning goals.
- Earned badges and XP.
- Progress over time.
- Available reports and sharing controls.

Provide filters for skills, assessment status, difficulty, and completion date where useful.

Every displayed metric must come from actual stored application data.

Do not use fabricated statistics or pretend that an assessment has occurred when it has not.

## 13. Assessment History and Progress Tracking

Maintain a chronological history of assessment attempts.

For each attempt, record the challenges completed, submission results, relevant metrics, and final outcome.

Allow candidates to compare repeated assessments and understand whether their skills are improving.

Maintain the original assessment evidence so that later reports do not silently rewrite historical outcomes when a challenge or scoring rubric changes.

Use versioned challenges and rubrics wherever necessary to preserve the meaning of historical results.

Clearly distinguish a genuinely comparable reassessment from an assessment that used substantially different tasks or criteria.

## 14. Recruiter Experience and Report Sharing

Provide a clean, read-only experience for reviewing a candidate's shared report.

The recruiter should be able to understand:
- What skill was assessed.
- Why the candidate chose to verify it.
- What level the candidate originally claimed, if stated.
- Which competencies were tested.
- What the candidate demonstrated.
- What the platform could not establish.
- Whether the available evidence is sufficient for the reported conclusion.

Do not rank candidates automatically using a single universal score.

Do not imply that a candidate with more badges is necessarily a stronger employee.

Keep conclusions proportional to the available evidence.

## 15. Administration and Challenge Quality

Provide a dedicated administrative area for managing assessment content.

Administrators should be able to:
- Create challenges.
- Edit challenge descriptions.
- Define expected behavior.
- Configure test cases and evaluation rubrics.
- Set challenge difficulty and time limits.
- Associate challenges with skills and competencies.
- Preview candidate-facing instructions.
- Review AI-generated challenge proposals.
- Validate expected answers and test cases.
- Publish, unpublish, and version challenges.
- Create learning resources and achievement definitions.

AI-generated challenges must remain unpublished until their expected outcomes and evaluation criteria have been validated.

Keep a record of important challenge changes so that assessment history remains interpretable.

## 16. Privacy, Integrity, and Fairness

Treat resumes, submissions, assessment results, and personal information as private data.

Implement appropriate authorization, secure report sharing, and data-retention controls.

Provide clear explanations of what information is stored and how it is used.

Do not expose one candidate's private information to another candidate or recruiter.

Do not treat a network interruption, failed infrastructure operation, or insufficient assessment as proof that a candidate lacks a skill.

Use consistent assessment criteria and clearly state any known limitations.

Do not claim that an assessment is completely cheat-proof or perfectly objective.

The system should provide useful evidence while acknowledging that short assessments cannot capture every aspect of professional competence.

## 17. Visual Design and User Experience

Create a polished, professional, responsive application suitable for a real recruitment product and an academic project demonstration.

The visual identity should communicate:
- Credibility.
- Technical competence.
- Transparency.
- Progress.
- Professional development.

Use consistent typography, spacing, color, iconography, and component styling.

Provide clear visual distinctions between the four verification statuses without relying on color alone.

Design intuitive screens for resume upload, skill review, challenge completion, assessment feedback, report viewing, and learning progress.

The challenge workspace should minimize distractions and make instructions, time remaining, submission controls, and results easy to understand.

Include useful loading indicators, empty states, validation messages, error recovery, and confirmation prompts for important actions.

Ensure that the application works on desktop, tablet, and mobile screen sizes.

Avoid decorative elements that make the interface look impressive but do not contribute to usability.

Every visible button, link, form, and navigation item must perform its intended action.

## 18. End-to-End Candidate Journey

The complete candidate journey must work as follows:

1. The candidate registers and creates a profile.
2. The candidate uploads a resume.
3. SkillTrial extracts relevant skills and stated proficiency claims.
4. The candidate reviews and confirms the extracted information.
5. The candidate selects a skill to verify.
6. SkillTrial presents relevant practical micro-challenges.
7. The candidate completes the timed assessment.
8. The platform evaluates submissions and records the supporting evidence.
9. The candidate completes an AI-Assisted Trust Challenge when included in the assessment.
10. SkillTrial generates a verification report with one of the four defined statuses.
11. The platform identifies skill gaps and recommends personalized practice.
12. The candidate completes learning activities and earns eligible rewards.
13. The candidate attempts new challenges to demonstrate improvement.
14. The candidate compares their assessment history.
15. The candidate downloads a report or shares selected results with a recruiter.
16. The candidate can revoke the shared report when access is no longer desired.

Each stage must be connected to the next. Data entered in one stage must persist and be reflected correctly throughout the application.

## 19. Expected Final Deliverable

Build a complete working implementation of SkillTrial, not merely a prototype consisting of disconnected screens.

The final application must include:
- Candidate registration and authentication.
- Resume upload and skill extraction.
- Candidate confirmation of extracted claims.
- Skill catalog and competency mapping.
- Practical micro-challenges.
- Timed assessments.
- Objective evaluation and evidence recording.
- AI-Assisted Trust Challenges.
- Four-state skill verification reports.
- Personalized learning paths.
- Gamification and progress tracking.
- Assessment history.
- Downloadable reports.
- Secure report sharing and revocation.
- Recruiter report-viewing experience.
- Administrative challenge management.
- Privacy and authorization controls.
- Useful demonstration data.
- Testing and setup documentation.

Use realistic examples and meaningful content. Do not leave essential workflows as static mockups.

If any feature cannot be fully implemented, clearly identify what works, what remains incomplete, and what is required to finish it.

## 20. Acceptance Criteria

The application will be considered complete only when all the following scenarios work:

- A candidate can upload a resume and review the extracted skills.
- A candidate can correct an extraction mistake before assessment.
- A candidate can complete a practical challenge and receive a result based on actual evaluation.
- The assessment deadline is enforced.
- Hidden test cases and answer keys are protected.
- An AI-Assisted Trust Challenge evaluates a candidate's technical judgment using validated criteria.
- Each skill receives an appropriate verification status supported by evidence.
- Insufficient evidence is not incorrectly classified as failure.
- Weak competencies lead to relevant learning recommendations.
- Completed learning activities update progress and eligible rewards correctly.
- A candidate can compare reassessment results without losing historical evidence.
- A candidate can download and share a report securely.
- A revoked share link no longer grants access.
- Recruiters cannot access unauthorized candidate information.
- Administrators can create, validate, and publish challenges.
- The application handles errors and incomplete assessments without fabricating results.
- All essential navigation and controls function correctly.
- The complete candidate journey can be demonstrated from registration through verification and report sharing.

## Final Instruction

Use this description as the definitive product specification.

First understand the complete product, define its information architecture, identify the required workflows, and plan the implementation.

Then build the application incrementally, test each major workflow, correct defects, and verify the acceptance criteria.

Make sensible implementation decisions without changing the product's core concept.

Prioritize functional completeness, reliable evidence, clear user experience, security, and honest assessment outcomes over unnecessary features.

The final result should make SkillTrial feel like a cohesive skill-verification and improvement platform, not simply a resume parser combined with a coding quiz website.
