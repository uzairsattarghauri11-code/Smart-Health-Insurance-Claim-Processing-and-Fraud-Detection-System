# Smart Health Insurance Claim Processing and Fraud Detection System
## Web Application (Flask)

A GUI-based web version of the claim processing system. Runs locally and opens
in your browser.

## Requirements
- Python 3.8 or newer
- Flask

## Setup (one time)

Open a terminal inside this folder (the folder containing `app.py`) and install Flask:

    pip install flask

If `pip` is not recognised on Windows, try:

    python -m pip install flask

## How to run

In the same folder, run:

    python app.py

On Mac/Linux use:

    python3 app.py

You will see output ending with a line like:

    Running on http://127.0.0.1:5000

Open that address in your web browser (Chrome, Edge, etc.):

    http://127.0.0.1:5000

To stop the server, press CTRL+C in the terminal.

## Demo login accounts

| Role          | Username        | Password  |
| ------------- | --------------- | --------- |
| Admin         | admin           | admin123  |
| Hospital      | city_hospital   | hosp123   |
| Hospital      | metro_clinic    | hosp123   |
| Officer       | officer1        | off123    |
| Policyholder  | ahmed           | pol123    |
| Policyholder  | uzair           | pol123    |

## Notes
- The app creates a file called `insurance_data.json` in this folder on first run.
  This stores all users, policies, claims, notifications, and the audit trail.
- The app comes pre-loaded with six sample claims so the dashboards look populated.
- To reset everything to the default seeded data, delete `insurance_data.json`
  and run the app again.

## Suggested screenshots for the report
1. Login screen
2. Hospital dashboard (login as city_hospital)
3. Claim submission form
4. Officer review screen (login as officer1 — "Claims Pending Review")
5. Policyholder claim tracking (login as uzair)
6. Admin dashboard and audit trail
