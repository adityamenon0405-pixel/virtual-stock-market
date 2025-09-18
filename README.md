
## Deployment Instructions

### Backend (Flask)
1. Deploy `backend.py` on [Render](https://render.com) or [Railway](https://railway.app)
2. Start command: `gunicorn backend:app`
3. Copy the public backend URL (e.g., `https://your-backend-service.onrender.com`)

### Frontend (Streamlit)
1. Update `API_URL` in `frontend.py` with your backend URL
2. Push `frontend.py` and `requirements.txt` to GitHub
3. Deploy on [Streamlit Community Cloud](https://share.streamlit.io)

## Dependencies
- flask
- gunicorn
- streamlit
- requests
- pandas
- plotly

## How to Use
1. Open the frontend app
2. Enter your username and register/login
3. Buy and sell stocks
4. Monitor portfolio and leaderboard
5. Watch live charts update every 10 seconds
