# Prompt: Critique and Select Interface

Act as a product design review panel evaluating the different NoteWise interface concepts.

The goal is to identify the direction that best supports learning and source verification, not simply the most visually attractive interface.

## Product Context

NoteWise is a personalized learning system based on lecture materials.

The main workflow is:

**Open lecture material → read → ask AI → verify citations → continue learning.**

The interface must support both learning and verification of AI-generated answers.

## Scoring Criteria

Score each concept from 1-5 for the following criteria and explain each score using specific observations:

### 1. Focus on the Primary Learning Task

Does the interface keep the learner focused on reading and understanding the lecture material?

### 2. Document and Conversation

Can users comfortably read the document and view the AI conversation in parallel?

### 3. Citation Findability

Can users quickly find and understand page/slide citations?

Can users identify which source passage supports an AI answer?

### 4. AI State Awareness

Can users recognize when the AI is:

- Processing
- Ready
- Unable to answer
- Experiencing an error

Does the interface provide a clear recovery action?

### 5. Product Scalability

Can the interface scale to additional NoteWise features such as:

- Summaries
- Quizzes
- Analytics
- Weak-topic analysis
- Learning recommendations
- Learning history

### 6. Accessibility and Responsiveness

Evaluate:

- Keyboard accessibility
- Visible focus states
- Text readability
- Color contrast
- Responsive behavior
- Mobile usability

### 7. Suitability for New Learners

Can a first-time user understand what to do without extensive instructions?

### 8. Implementation Cost and UI Complexity

Consider:

- Number of components
- Layout complexity
- Interaction complexity
- Responsive implementation
- Potential maintenance cost

## Critical Questions

Use the following questions when reviewing each concept:

### Question 1

Which components compete with the learning content?

### Question 2

Can users clearly tell which passage the AI answer is based on?

### Question 3

What does the UI communicate when the document is still processing?

### Question 4

What happens when the AI cannot find enough information in the source document?

### Question 5

Is the next learning action clearer than simply viewing a dashboard?

### Question 6

Does the layout remain usable on small screens?

### Question 7

What happens when citations or source references become long?

### Question 8

Do charts, badges, or colors create a false sense of AI accuracy?

## Output Format

Create a scoring table using the following structure:

| Criterion | Concept 1 | Concept 2 | Concept 3 | Key Observation |
|---|---:|---:|---:|---|
| Primary learning focus | | | | |
| Document + Q&A | | | | |
| Citation clarity | | | | |
| AI state awareness | | | | |
| Scalability | | | | |
| Accessibility | | | | |
| New learner suitability | | | | |
| Implementation complexity | | | | |

Then provide:

### Issues by Severity

#### Critical

List issues that could prevent users from completing the main learning workflow.

#### High

List issues that significantly reduce clarity, trust, or usability.

#### Medium

List issues that should be improved but do not block the main workflow.

#### Low

List visual or minor interaction improvements.

## Recommended Changes

For the concept selected for further development, describe:

- Layout changes
- Navigation changes
- Citation improvements
- AI state improvements
- Accessibility improvements
- Responsive improvements
- Component changes

## Validation Questions

List questions that should be tested with real users before implementation.

Examples:

- Can users find the source of an AI answer?
- Can users distinguish AI-generated content from original lecture content?
- Can users understand why an answer cannot be generated?
- Can users find the next recommended learning action?
- Can users complete the workflow on a mobile device?

## Final Decision

State which interface direction should be taken forward based on the documented criteria and evidence from the review.

Do not base the decision only on visual preference.

The selected direction should be justified by its ability to support NoteWise's core learning workflow, source verification, accessibility, scalability, and implementation requirements.
