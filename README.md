# Virtual Stock Market Game

## How to Deploy

### Backend
1. Deploy `backend.py` to Render or Railway.
2. Start command: `gunicorn backend:app`
3. Note the public URL, e.g., `https://your-backend-service.onrender.com`

### Frontend
1. Update `API_URL` in `frontend.py` to point to the backend URL.
2. Push to GitHub.
3. Deploy `frontend.py` on Streamlit Community Cloud.
