# Guide de Contribution - Rebbah AI

Merci de contribuer au projet Rebbah AI ! Afin de maintenir un code de haute qualité et une collaboration fluide, ce document définit les règles de développement et le flux de travail (workflow) à respecter par toute l'équipe.

## 1. Stratégie des Branches

Notre dépôt repose sur deux branches principales qui sont **protégées** :
- `main` : La branche de production. Le code ici est stable et correspond à ce qui est déployé.
- `dev` : La branche d'intégration de développement. Toutes les nouvelles fonctionnalités sont regroupées ici avant d'être envoyées sur `main`.

> ⚠️ **RÈGLE CRITIQUE : Il est strictement interdit d'effectuer un commit ou un `git push` directement sur les branches `dev` et `main`.** Toute modification du code sur ces branches doit obligatoirement passer par une **Pull Request (PR)**.

### Création de votre branche de travail
Toute modification doit être faite dans une nouvelle branche, créée à partir de la branche `dev`. Veuillez utiliser les préfixes suivants pour nommer votre branche :

- `feat/nom-de-la-fonctionnalite` : Ajout d'une nouvelle fonctionnalité.
- `fix/nom-du-bug` : Correction d'un bug.
- `chore/tache-de-maintenance` : Tâches de maintenance (ex: mise à jour de librairies, configuration).
- `docs/nom-du-document` : Ajout ou modification de la documentation.
- `refactor/nom-du-refactoring` : Refonte de code sans ajout de fonctionnalité ni correction de bug.

**Exemple :**
```bash
git checkout dev
git pull origin dev
git checkout -b feat/ajout-authentification
```

## 2. Processus de Développement et Pull Request (PR)

Pour intégrer votre code dans `dev` ou `main`, vous devez suivre ces étapes :

### Étape 1 : Développement et Commits
- Codez vos modifications sur votre branche.
- Assurez-vous que votre code passe les tests existants et qu'il respecte les normes de formatage du projet.
- Faites des commits réguliers, logiques, avec des messages clairs (ex: `feat: ajoute la connexion au compte utilisateur`).

### Étape 2 : Push de la branche
- Une fois votre travail terminé (ou prêt pour une relecture), poussez votre branche sur le dépôt distant :
  ```bash
  git push -u origin votre-branche
  ```

### Étape 3 : Ouverture de la Pull Request (PR)
- Sur GitHub, ouvrez une Pull Request de votre branche vers la branche cible (généralement `dev`).
- Remplissez le modèle de description de la PR de manière détaillée : expliquez ce que fait votre code, pourquoi il a été fait de cette manière, et listez les problèmes résolus.

### Étape 4 : Validation par le Codeowner (Revue de Code)
- L'équipe utilise le système de *Codeowners*. **Votre Pull Request doit impérativement être validée (Approuvée) par les réviseurs (Codeowners) désignés.**
- Les réviseurs liront votre code, feront des commentaires et pourront demander des ajustements.
- S'il y a des retours, effectuez les modifications sur votre branche locale, faites de nouveaux commits et poussez-les (`git push`). La PR se mettra à jour automatiquement.

### Étape 5 : Fusion (Merge)
- Une fois que la PR obtient l'approbation (`Approve`) du Codeowner, **et** que tous les éventuels tests automatisés certifient le bon fonctionnement, la branche pourra être fusionnée (`Merge`) dans `dev` (ou `main`).
- La fusion doit être faite via l'interface GitHub, idéalement en mode "Squash and merge" ou "Rebase and merge" afin de garder un historique propre.
- Une fois la PR mergée, vous pouvez supprimer votre branche de travail.

## Codeowners

Les réviseurs obligatoires sont définis dans le fichier `CODEOWNERS` (ou dans la configuration de GitHub). GitHub les assignera automatiquement comme `Reviewers` de vos PRs selon les dossiers et fichiers touchés.
