# GitHub Repository Setup Instructions

Follow these steps to push this project to your GitHub repository:

## 1. Create a new repository on GitHub

1. Go to [GitHub](https://github.com/) and sign in
2. Click on the "+" icon in the top right corner and select "New repository"
3. Name the repository "Stock-Analyzer"
4. Choose whether you want it to be public or private
5. Click "Create repository"

## 2. Download or Export this Replit project

There are several ways to get the code from Replit:
- Use the "Download as zip" option from the three-dot menu
- Clone the Replit project using the Git URL

## 3. Set up the local repository and push to GitHub

Once you have the code on your local machine:

```bash
# Navigate to the project directory
cd path/to/Stock-Analyzer

# Initialize a new git repository
git init

# Add all files to the repository
git add .

# Commit the files
git commit -m "Initial commit"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/Stock-Analyzer.git

# Push to GitHub
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## 4. Dependencies

Make sure to include these dependencies in your requirements.txt:

```
streamlit>=1.30.0
pandas>=2.2.0
numpy>=1.26.0
plotly>=5.18.0
yfinance>=0.2.33
sqlalchemy>=2.0.25
```

## 5. Running the app

After cloning the repository:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```