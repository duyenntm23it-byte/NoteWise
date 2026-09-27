# Prompt: Explore Interface Directions

Create three different UI concepts for NoteWise using HTML/CSS that can be opened directly in a browser.

Each concept must focus on the same workflow:

**The learner opens a document → reads the content → asks the AI assistant a question.**

## Product Context

NoteWise transforms PDF/PPTX lecture materials into an AI-powered learning experience.

Answers must include page/slide citations.

Users need to switch quickly between:

- Summaries
- Document Q&A
- Quizzes
- Weak-topic analytics
- Learning recommendations

The interface should help learners stay focused on the learning content while making AI-generated answers and their sources easy to verify.

## Concepts to Explore

### Concept 1 - Focused Study Desk

Create a quiet digital study desk.

The main area should provide a large document-reading canvas, while a compact AI assistant panel stays visible on the side.

The layout should minimize distractions and make reading the lecture material the primary activity.

Include:

- Document title
- Page/slide navigation
- Reading area
- AI assistant panel
- Question input
- Citation cards
- Loading state
- Empty state

### Concept 2 - Evidence-First Workspace

Create a workspace where citations, sources, and related passages are the center of the experience.

When the AI answers a question, the user should immediately see:

- The answer
- The source document
- Page/slide number
- Relevant section
- Related passage

Clicking a citation should highlight the related content in the document reader.

The interface should visually distinguish AI-generated content from source content.

### Concept 3 - Progressive Learning Hub

Create an interface that emphasizes the learner's progress and next learning action.

The main screen should still provide document reading and AI Q&A, but it should also make the next useful activity obvious.

Possible next actions include:

- Review this topic
- Take a 5-question quiz
- Read the referenced pages
- Practice a weak topic
- Continue learning

The interface should avoid overwhelming the learner with too many actions at once.

## Required Interface Elements

Each concept must include:

- Header or sidebar navigation
- Document area
- Q&A area
- At least two conversation messages
- Citation card
- Question input
- Loading or empty state
- Responsive mobile layout

Use sample data written in English.

Use intentional typography and clear hierarchy.

## Technical Constraints

- Tailwind CSS may be used through a CDN for a single-file prototype.
- Do not use a JavaScript framework that requires a build step.
- Do not use copyrighted assets or images that require downloading.
- Use simple layouts, colors, typography, and text icons where appropriate.
- Buttons and inputs must have basic accessibility labels.
- The prototype must work when opened directly in a browser.

## Output

Return HTML/CSS for all three concepts.

After each concept, provide a short design note covering:

1. Strengths
2. Risks
3. Suitable users
4. Questions that should be validated through usability testing

The three concepts should be visually and structurally different enough to support meaningful comparison.
