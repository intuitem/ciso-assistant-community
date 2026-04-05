---
title: Politique de réponse aux incidents
description: Procédures de détection, de réponse et de reprise suite aux incidents de sécurité
---

# Politique de réponse aux incidents

## 1. Objet

La présente politique établit le cadre d'identification, de gestion et de résolution des incidents de sécurité de l'information. Elle garantit une approche cohérente et efficace du traitement des incidents, en minimisant leur impact et en permettant une reprise rapide.

## 2. Périmètre d'application

Cette politique couvre l'ensemble des incidents de sécurité de l'information affectant les systèmes, les données, le personnel ou les opérations de l'organisation, y compris :
- Les accès non autorisés aux systèmes ou données
- Les infections par logiciels malveillants
- Les violations ou pertes de données
- Les attaques par déni de service
- Les attaques par ingénierie sociale
- Les atteintes à la sécurité physique impactant les actifs informationnels

## 3. Classification des incidents

### 3.1 Niveaux de gravité

| Niveau | Description | Exemples |
|--------|-------------|----------|
| Critique | Impact significatif sur les opérations ou les données | Violation de données, rançongiciel, panne totale |
| Élevé | Impact majeur nécessitant une attention immédiate | Accès non autorisé aux données sensibles, panne partielle |
| Moyen | Impact modéré avec un périmètre limité | Logiciel malveillant sur un seul système, violation de politique |
| Faible | Impact mineur, aucune perte de données | Tentative d'intrusion échouée, écart mineur de politique |

## 4. Phases de réponse aux incidents

### 4.1 Préparation
- Maintenir une équipe de réponse aux incidents avec des rôles et responsabilités définis
- S'assurer que les membres de l'équipe sont formés et mener des exercices réguliers
- Maintenir à jour les listes de contacts et les procédures d'escalade
- Déployer et maintenir les outils de détection et de surveillance

### 4.2 Détection et analyse
- Surveiller les systèmes et réseaux pour détecter les indicateurs de compromission
- Analyser les alertes pour déterminer le périmètre et la gravité
- Documenter les constatations initiales et classifier l'incident
- Notifier les parties prenantes appropriées en fonction de la gravité

### 4.3 Confinement
- Mettre en œuvre un confinement à court terme pour limiter les dommages immédiats
- Préserver les preuves pour l'analyse forensique
- Mettre en œuvre des mesures de confinement à long terme si nécessaire
- Communiquer l'état du confinement aux parties prenantes

### 4.4 Éradication
- Identifier et éliminer la cause racine
- Supprimer les logiciels malveillants, les accès non autorisés ou autres menaces
- Corriger les vulnérabilités exploitées
- Vérifier que la menace a été complètement éliminée

### 4.5 Reprise
- Restaurer les systèmes affectés à partir de sauvegardes propres
- Vérifier l'intégrité des systèmes avant leur remise en production
- Surveiller les systèmes restaurés pour détecter tout signe de récurrence
- Rétablir progressivement les opérations avec une surveillance renforcée

### 4.6 Retour d'expérience
- Mener un retour d'expérience dans les 5 jours ouvrables suivant l'incident
- Documenter les enseignements tirés et les recommandations
- Mettre à jour les politiques, procédures et mesures de sécurité en conséquence
- Partager les constatations pertinentes avec les équipes concernées

## 5. Obligations de signalement

- Tout incident suspecté doit être signalé immédiatement à l'équipe sécurité
- Les incidents de gravité critique et élevée doivent être signalés à la direction dans les 4 heures
- Les notifications réglementaires doivent être effectuées dans les délais requis
- Les personnes concernées doivent être notifiées conformément à la législation

## 6. Rôles et responsabilités

### 6.1 Équipe de réponse aux incidents
- Diriger l'investigation et la coordination des incidents
- Prendre les décisions de confinement et d'éradication
- Produire les rapports d'incident et les recommandations

### 6.2 Ensemble des collaborateurs
- Signaler rapidement les incidents suspectés
- Coopérer aux investigations sur les incidents
- Suivre les instructions de l'équipe de réponse aux incidents

### 6.3 Direction
- Fournir les ressources et le soutien nécessaires à la réponse aux incidents
- Prendre les décisions métier liées à l'impact des incidents
- Approuver les communications vers les parties externes

## 7. Gestion des preuves

- Les preuves doivent être collectées et conservées selon les bonnes pratiques forensiques
- La chaîne de traçabilité doit être maintenue et documentée
- Les preuves doivent être stockées de manière sécurisée et conservées conformément aux exigences légales

## 8. Communication

- Les communications internes doivent suivre les procédures d'escalade établies
- Les communications externes (médias, régulateurs, clients) doivent être coordonnées par les porte-paroles autorisés
- Des modèles de communication doivent être maintenus et mis à jour régulièrement

## 9. Révision de la politique

Cette politique doit être révisée au moins annuellement et après chaque incident de sécurité majeur. Le plan de réponse aux incidents doit être testé par des exercices de simulation au moins deux fois par an.
