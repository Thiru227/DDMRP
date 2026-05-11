## ADDED Requirements

### Requirement: Role-based login
The system SHALL authenticate users via a login screen before any app page is accessible. Three roles exist: admin, planner, executor. Credentials are hardcoded for POC (`admin/admin`, `planning/planning`, `executer/executer`). On success a Flask server-side session is created.

#### Scenario: Successful admin login
- **WHEN** user selects the Admin role card, enters username `admin` and password `admin`, and clicks Sign In
- **THEN** system creates a session with role `admin`, redirects to the app shell, and the Admin nav section is visible

#### Scenario: Successful planner login
- **WHEN** user selects the Planning role card, enters username `planning` and password `planning`, and clicks Sign In
- **THEN** system creates a session with role `planner`, and only the Planning nav section is visible (Alert Dashboard, Order Recommendation, Hub Allocation, PO Tracking)

#### Scenario: Successful executor login
- **WHEN** user selects the Execution role card, enters `executer`/`executer`, and clicks Sign In
- **THEN** system creates a session with role `executor`, and only the Execution nav section is visible (Inbox, PO Review, Released, PO Tracking)

#### Scenario: Wrong credentials
- **WHEN** user enters invalid username or password
- **THEN** system shows an inline error message and does NOT create a session

#### Scenario: Session check on page load
- **WHEN** the app shell page loads
- **THEN** JS reads `window.__SESSION__` injected by Flask; if no session exists, the login screen is shown immediately without an API round-trip

### Requirement: Logout
The system SHALL allow any logged-in user to log out.

#### Scenario: Logout clears session
- **WHEN** user clicks the user avatar/name in the sidebar footer
- **THEN** `POST /api/auth/logout` is called, session is cleared, and the login screen is shown
