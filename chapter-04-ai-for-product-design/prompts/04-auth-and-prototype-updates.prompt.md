# Prompt: Update UI/UX, Guest/Logged-in Permissions, and Complete the NoteWise Prototype

You are a UI/UX Expert and Frontend Architect. Update the NoteWise prototype in the `prototype/` directory based on the permission rules, interface changes, and detailed interaction states described below.

## 1. Guest vs. Logged-in Permissions

Simulate the login state using `localStorage` (`isLoggedIn = true/false`) in `script.js`, without requiring a backend.

### Guest Mode (`isLoggedIn === false`)

- **Top Header**: Display the [Log In] and [Sign Up] buttons on the right instead of the avatar.
- **Dashboard**: Display static sample data.
- **Materials**: Allow access to only 1–2 sample documents. Hide or disable the buttons for uploading new files and deleting files.
- **Q&A and AI Summary**: Allow questions and answers based on sample documents, with a limited number of interactions.
- **Take Quiz**: Allow the user to complete one demo quiz. When the quiz is submitted, display a clear message: _"⚠️ Your result was not saved because you are not logged in. [Log in now]"_.
- **Analytics / Recommendations / History**: Display an empty-state panel with an illustration and the CTA button _"Log in to view your personal progress"_ (do not silently lock these features).

### Logged-in Mode (`isLoggedIn === true`)

- **Top Header**: Display the `AT` avatar (An Ton), the user's name, and a [Log Out] button.
- Unlock all features: upload personal documents, automatically save quiz results, view analytics charts showing weak topic areas, and receive personalized learning recommendations.

---

## 2. Screen-specific UI Changes

### Screen 1: Authentication (Auth)

- Integrate an authentication form with tabs: **[Log In]** and **[Sign Up]**.
- Sign-up tab: Add a "Confirm Password" field and change the submit button label to "Create Account".
- When the user submits the Log In or Sign Up form, set `isLoggedIn = true`, save the state in `localStorage`, return to the Dashboard, and change the header to show the avatar.

### Screen 2: Materials Library (Materials)

- Simplify the filters: Keep only the **Status Filter** (Ready / Processing / Failed). Remove the Subject and Tag filters.

### Screen 4: AI Quiz (Player & Results)

- **Automatic saving**: Remove the [Save Result] button. Replace it with a simulated automatic-save status label that changes from _"Saving..."_ to _"Saved"_.
- **Support different question types**:
  - Multiple-choice / True-False: Use radio buttons (`<input type="radio">`).
  - Fill-in-the-blank: Use a text input (`<input type="text">`).
- **Results screen**: Display a separate **[Skipped]** badge for unanswered questions. Do not include them in the "Incorrect" question count.

### Screen 5: Analytics

- Change the metric: Replace "Number of mastered documents" with **"Number of topics with sufficient data"**.
- Weak-topic alerts: Display a risk-warning card only when a topic has at least 2 attempts (`>= 2`) in `mock-data.js`. If there are not enough attempts, display the banner _"Not enough evidence for analysis"_.

### Screen 6: Learning Recommendations

- Simulate two states:
  1. _Relevant documents available_: Display the exact number of cited pages/slides from `mock-data.js`.
  2. _No relevant documents available_: Display the message _"You don't have any documents about this topic yet"_ with the CTA button _"Upload more documents"_.

---

## 3. Additional Exception States (UI Edge Cases)

Create simulated notification modals/toasts in JavaScript for the following cases:

1. **Insufficient content**: Show a notification when a document is too short to generate a quiz or summary.
2. **Invalid AI output**: Display a "Try Again (Retry)" button when the AI returns an error or an invalid response.
3. **Unauthorized access / Expired session**: Automatically switch back to Guest Mode and show a modal prompting the user to log in again.

---

## 4. Deliverables

- Create the file `chapter-04-ai-for-product-design/prompts/04-auth-and-prototype-updates.prompt.md`.
- Update the HTML/JS/CSS files in `chapter-04-ai-for-product-design/prototype/` to fully implement all the rules above.
