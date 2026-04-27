---
title: "Politique de cryptographie et de chiffrement"
description: "Normes d'utilisation des moyens cryptographiques et du chiffrement pour la protection de l'information"
---

# Politique de cryptographie et de chiffrement

## 1. Objet

Cette politique définit les exigences relatives à l'utilisation des moyens cryptographiques pour protéger la confidentialité, l'intégrité et l'authenticité des informations au sein de [Nom de l'organisation].

## 2. Périmètre

Cette politique s'applique à l'ensemble des systèmes, applications et données détenus ou gérés par [Nom de l'organisation], y compris les données au repos, les données en transit et les données en cours de traitement.

## 3. Normes de chiffrement

### 3.1 Données au repos

- Toutes les données sensibles et confidentielles stockées sur les serveurs, bases de données et supports de stockage doivent être chiffrées.
- Le chiffrement intégral du disque doit être activé sur tous les terminaux (ordinateurs portables, postes de travail, appareils mobiles).
- Algorithmes approuvés : AES-256 pour le chiffrement symétrique.

### 3.2 Données en transit

- Toutes les communications réseau transportant des données sensibles doivent utiliser des canaux chiffrés.
- TLS 1.2 ou supérieur est requis pour toutes les communications web et API.
- Les protocoles obsolètes (SSL, TLS 1.0, TLS 1.1) sont interdits.
- Les connexions VPN doivent utiliser des normes de chiffrement approuvées pour l'accès distant.

### 3.3 Données en cours de traitement

- Dans la mesure du possible, le chiffrement au niveau applicatif doit être utilisé pour le traitement des données sensibles.
- Le chiffrement au niveau des champs de base de données doit être appliqué aux champs hautement sensibles (identifiants d'authentification, données financières).

## 4. Gestion des clés

### 4.1 Génération des clés

- Les clés cryptographiques doivent être générées à l'aide de générateurs de nombres aléatoires approuvés.
- Les longueurs de clés doivent respecter ou dépasser les recommandations actuelles de l'industrie.

### 4.2 Stockage et protection des clés

- Les clés privées ne doivent jamais être stockées en clair.
- Des modules matériels de sécurité (HSM) ou des services de gestion de clés équivalents doivent être utilisés pour les clés critiques.
- L'accès aux clés cryptographiques doit être limité au personnel autorisé uniquement.

### 4.3 Rotation et expiration des clés

- Les clés de chiffrement doivent faire l'objet d'une rotation selon un calendrier défini basé sur l'analyse des risques.
- Les clés compromises ou suspectées de l'être doivent être révoquées et remplacées immédiatement.
- Les clés expirées doivent être archivées de manière sécurisée ou détruites conformément aux exigences de conservation.

### 4.4 Destruction des clés

- Les clés devenues inutiles doivent être détruites de manière sécurisée selon des méthodes approuvées.
- La destruction des clés doit être documentée et auditable.

## 5. Gestion des certificats

- Les certificats numériques doivent être émis par des autorités de certification de confiance.
- L'expiration des certificats doit être surveillée et les renouvellements effectués avant l'échéance.
- Les certificats auto-signés sont interdits dans les environnements de production.

## 6. Pratiques interdites

- L'utilisation d'algorithmes de chiffrement propriétaires ou non éprouvés est interdite.
- Le codage en dur des clés de chiffrement dans le code source est interdit.
- La transmission de clés de chiffrement via des canaux non chiffrés est interdite.
- La désactivation ou le contournement des contrôles de chiffrement sans approbation documentée est interdit.

## 7. Rôles et responsabilités

- **Équipe Sécurité SI** : Définir les normes de chiffrement, gérer l'infrastructure de gestion des clés et mener les revues de conformité.
- **Administrateurs systèmes** : Mettre en oeuvre et maintenir le chiffrement sur les systèmes et l'infrastructure.
- **Développeurs** : Appliquer les normes de chiffrement dans le développement applicatif et assurer une gestion sécurisée des clés.
- **Tous les collaborateurs** : Respecter les exigences de chiffrement pour la manipulation des données et l'utilisation des équipements.

## 8. Conformité

Les violations de cette politique peuvent entraîner des mesures disciplinaires pouvant aller jusqu'au licenciement. Le non-respect peut également exposer [Nom de l'organisation] à des sanctions légales et réglementaires.

## 9. Revue de la politique

Cette politique doit être révisée au moins une fois par an ou en cas de changement significatif du paysage des menaces, de l'environnement technologique ou des exigences réglementaires.
