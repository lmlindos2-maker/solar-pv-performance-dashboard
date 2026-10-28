# Solar PV Streamlit Dashboard

## Files
- `app.py`: Streamlit dashboard application
- `requirements.txt`: Python package dependencies
- `SolarPV_Cleaned_Data.csv`: add your dataset here, or upload it in the dashboard sidebar

## Run locally
1. Install Python 3.10 or later.
2. Open a terminal in this folder.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Put `SolarPV_Cleaned_Data.csv` in this folder, or launch the app and upload the CSV using the sidebar.
5. Run:
   `streamlit run app.py`

The dashboard expects columns including `AC_POWER`, `IRRADIATION`, and `MODULE_TEMPERATURE`. It uses `DATE_TIME` for date/time charts and filters when available.

## Deployment
Upload `app.py`, `requirements.txt`, and `SolarPV_Cleaned_Data.csv` to a GitHub repository, then deploy the repository using Streamlit Community Cloud. If you do not want the dataset stored in the repository, omit the CSV and upload it through the app's sidebar (note that the app's viewer will then need to upload it too).
