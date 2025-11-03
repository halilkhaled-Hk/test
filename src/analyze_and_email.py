import os
import subprocess
import sys
from google import genai
from google.genai import types
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
COMMIT_AUTHOR_EMAIL = os.environ.get("COMMIT_AUTHOR_EMAIL")
COMMIT_SHA = os.environ.get("COMMIT_SHA")

# Modèle Gemini à utiliser
GEMINI_MODEL = 'gemini-2.5-flash' 

if not all([GEMINI_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, COMMIT_AUTHOR_EMAIL]):
    print("Erreur: Les variables d'environnement nécessaires ne sont pas toutes définies.")
    # Le workflow échouera si les secrets ne sont pas configurés
    sys.exit(1)

# --- Fonctions Utilitaires ---

def get_modified_files():
    """Récupère la liste des fichiers modifiés dans le dernier commit."""
    try:
        # Récupère les fichiers modifiés dans le dernier commit (HEAD)
        # 'M' pour Modified, 'A' pour Added, 'D' pour Deleted (on ignore les suppressions)
        result = subprocess.run(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', COMMIT_SHA],
            capture_output=True, text=True, check=True
        )
        files = result.stdout.strip().split('\n')
        # Filtre les fichiers qui existent et ne sont pas des fichiers de configuration/workflow
        return [f for f in files if f and os.path.exists(f) and not f.startswith('.github/')]
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la récupération des fichiers modifiés: {e}")
        return []

def analyze_code_with_gemini(file_path):
    """Envoie le contenu d'un fichier à Gemini pour analyse."""
    try:
        with open(file_path, 'r') as f:
            code_content = f.read()
        
        # Le prompt pour Gemini
        prompt = f"""
        Analyse le code suivant du fichier '{file_path}'.
        
        Ton analyse doit être structurée et concise, en français.
        1. **Résumé** : Un bref résumé de ce que fait le code.
        2. **Erreurs/Problèmes** : Liste les erreurs potentielles, les bugs, les failles de sécurité ou les mauvaises pratiques. Si aucune, indique 'Aucun problème majeur détecté.'
        3. **Suggestions d'Amélioration** : Propose des améliorations de performance, de lisibilité ou de style.
        
        --- CODE ---
        {code_content}
        --- FIN CODE ---
        
        Formate ta réponse en Markdown.
        """
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        return f"Erreur lors de l'appel à l'API Gemini pour {file_path}: {e}"

def create_html_report(analysis_results):
    """Génère le corps de l'email au format HTML."""
    
    # Style CSS pour un email esthétique
    css_style = """
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        .header { background-color: #007bff; color: white; padding: 15px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 20px 0; }
        .file-section { margin-bottom: 30px; padding: 15px; border: 1px solid #eee; border-left: 5px solid #007bff; border-radius: 4px; }
        .file-header { font-size: 1.2em; color: #007bff; margin-top: 0; }
        h3 { border-bottom: 2px solid #eee; padding-bottom: 5px; color: #555; }
        pre { background-color: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; text-align: center; font-size: 0.9em; color: #777; }
    </style>
    """
    
    # Corps du rapport
    report_body = f"""
    <div class="container">
        <div class="header">
            <h1>Rapport d'Analyse de Code Automatisé</h1>
        </div>
        <div class="content">
            <p>Bonjour,</p>
            <p>Ce rapport contient l'analyse des fichiers que vous avez récemment commités (SHA: <code>{COMMIT_SHA[:7]}</code>) sur la branche principale.</p>
            
            {''.join(analysis_results)}
            
            <p>L'analyse a été effectuée par le modèle Gemini.</p>
        </div>
        <div class="footer">
            <p>Système d'Automatisation GitHub - {GMAIL_ADDRESS}</p>
        </div>
    </div>
    """
    
    return f"<html><head>{css_style}</head><body>{report_body}</body></html>"

def send_email(recipient_email, subject, html_content):
    """Envoie l'email HTML via SMTP (Gmail)."""
    
    msg = MIMEMultipart('alternative')
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # Attache le contenu HTML
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        # Connexion au serveur SMTP de Gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        
        # Connexion avec le mot de passe d'application
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        
        # Envoi de l'email
        server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())
        server.close()
        
        print(f"Email de rapport envoyé avec succès à {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return False

# --- Logique Principale ---

def main():
    print(f"Démarrage de l'analyse pour l'auteur: {COMMIT_AUTHOR_EMAIL}")
    
    modified_files = get_modified_files()
    
    if not modified_files:
        print("Aucun fichier pertinent modifié. Fin du processus.")
        return

    print(f"Fichiers à analyser: {modified_files}")
    
    all_analysis_html = []
    
    for file_path in modified_files:
        print(f"Analyse du fichier: {file_path}...")
        analysis_text = analyze_code_with_gemini(file_path)
        
        # Conversion simple du Markdown de Gemini en HTML pour l'email
        # Remplace les en-têtes Markdown par des balises HTML et les sauts de ligne par   

        html_analysis = analysis_text.replace('###', '<h4>').replace('##', '<h3>').replace('\n', '  
')
        
        file_html_section = f"""
        <div class="file-section">
            <h2 class="file-header">Fichier: <code>{file_path}</code></h2>
            {html_analysis}
        </div>
        """
        all_analysis_html.append(file_html_section)

    if not all_analysis_html:
        print("Aucune analyse n'a pu être générée.")
        return

    # Génération du rapport final
    final_html_report = create_html_report(all_analysis_html)
    
    # Envoi de l'email
    subject = f"Rapport d'Analyse de Code pour le Commit {COMMIT_SHA[:7]}"
    send_email(COMMIT_AUTHOR_EMAIL, subject, final_html_report)

if __name__ == "__main__":
    main()
