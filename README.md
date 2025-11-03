# Projet d'Automatisation d'Analyse de Code

Ce dépôt contient un workflow GitHub Actions qui s'exécute à chaque `push` sur la branche principale (`main`).

Le workflow effectue les actions suivantes :
1.  Récupère les fichiers modifiés par le commit.
2.  Envoie le contenu de chaque fichier à l'API Gemini pour une analyse de code (erreurs, suggestions, résumé).
3.  Compile les résultats dans un rapport HTML.
4.  Envoie le rapport par email à l'auteur du commit via Gmail.

## Configuration

Assurez-vous d'avoir configuré les secrets GitHub suivants :
*   `GEMINI_API_KEY` : Clé d'accès à l'API Gemini.
*   `GMAIL_ADDRESS` : Adresse Gmail de l'expéditeur.
*   `GMAIL_APP_PASSWORD` : Mot de passe d'application Gmail (nécessaire pour l'envoi d'emails via script).

## Utilisation

Après avoir configuré les secrets et créé les fichiers, tout `push` sur la branche `main` déclenchera automatiquement l'analyse et l'envoi du rapport par email à l'auteur du commit.
