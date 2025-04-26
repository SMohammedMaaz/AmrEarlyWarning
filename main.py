from app import app

# This file is used by gunicorn to run the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
