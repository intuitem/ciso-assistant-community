---
title: Hozzáférés-felügyeleti szabályzat
description: Az információs rendszerekhez és adatokhoz való hozzáférést szabályozó szabályzat
---

# Hozzáférés-felügyeleti szabályzat

## 1. Cél

Ez a szabályzat rögzíti a szervezet információs rendszereihez, alkalmazásaihoz és adataihoz való hozzáférés felügyeletére vonatkozó követelményeket. Biztosítja, hogy a hozzáférést az üzleti szükséglet és a legkisebb jogosultság elve alapján adják meg.

## 2. Hatály

A szabályzat hatálya kiterjed a szervezet információs rendszereihez, hálózataihoz, alkalmazásaihoz és adataihoz való minden hozzáférésre, a hozzáférés helyétől és módjától függetlenül.

## 3. Hozzáférés-felügyeleti elvek

- **Legkisebb jogosultság elve**: a felhasználóknak a feladataik ellátásához szükséges legkisebb mértékű hozzáférést kell biztosítani
- **Szükséges ismeret elve**: az információkhoz való hozzáférést azokra a személyekre kell korlátozni, akiknek a szerepkörükhöz szükségük van rá
- **Felelősségek szétválasztása**: a kritikus feladatköröket több személy között kell megosztani a csalás vagy a hiba kockázatának csökkentése érdekében

## 4. Felhasználói fiókok kezelése

### 4.1 Fiókok létrehozása
- Fiókot csak a felhasználó vezetőjétől érkező, engedélyezett kérelem alapján szabad létrehozni
- Minden felhasználónak egyedi azonosítóval kell rendelkeznie
- Az általános vagy megosztott fiókok használata tilos, kivéve, ha az műszakilag szükséges és jóváhagyott

### 4.2 Fiókok módosítása
- A hozzáférési jogosultságokat módosítani kell, ha a felhasználó szerepköre megváltozik
- A vezetők felelőssége, hogy csapatuk tagjai számára kérelmezzék a hozzáférés módosítását

### 4.3 Fiókok megszüntetése
- A munkaviszony megszűnésekor a hozzáférést azonnal vissza kell vonni
- Más szerepkörbe való áthelyezéskor a hozzáférést felül kell vizsgálni és ki kell igazítani
- A nem használt fiókokat 90 nap inaktivitás után le kell tiltani

## 5. Hitelesítés

### 5.1 Jelszókövetelmények
- A jelszavaknak meg kell felelniük a minimális összetettségi követelményeknek
- A jelszavakat rendszeres időközönként meg kell változtatni
- A jelszavak újrafelhasználását korlátozni kell
- Az alapértelmezett jelszavakat telepítéskor azonnal meg kell változtatni

### 5.2 Többfaktoros hitelesítés
- A távoli hozzáféréshez MFA-t kell megkövetelni
- A privilegizált fiókokhoz MFA-t kell megkövetelni
- Az érzékeny rendszerekhez és adatokhoz való hozzáféréshez MFA-t kell megkövetelni

## 6. Privilegizált hozzáférés

- A privilegizált fiókokat nyilvántartásba kell venni, és név szerint meghatározott személyekhez kell rendelni
- A privilegizált hozzáférést csak szükség esetén és a szükséges legrövidebb ideig szabad használni
- Minden privilegizált műveletet naplózni és felügyelni kell
- A privilegizált hitelesítő adatokat jóváhagyott jelszótárolóban kell tárolni

## 7. Távoli hozzáférés

- Távoli hozzáférést csak jóváhagyott, biztonságos csatornákon keresztül szabad biztosítani (VPN, zero trust)
- A felhasználóknak nem szabad magáneszközt használniuk távoli hozzáférésre, kivéve, ha az eszközt regisztrálták a mobileszköz-felügyeleti programban
- A távoli munkameneteket meghatározott idejű inaktivitás után meg kell szakítani

## 8. Hozzáférések felülvizsgálata

- Az érzékeny rendszerek esetében a felhasználók hozzáférési jogosultságait legalább negyedévente felül kell vizsgálni
- Minden hozzáférési jogosultságot legalább évente felül kell vizsgálni
- A felülvizsgálatokat dokumentálni kell, az eltéréseket pedig haladéktalanul ki kell javítani

## 9. Fizikai hozzáférés

- Az adatközpontokhoz és a szerverszobákhoz való fizikai hozzáférést a jogosult személyekre kell korlátozni
- A látogatók belépését naplózni kell, a látogatókat pedig kísérni kell
- A fizikai hozzáférési jogosultságokat rendszeresen felül kell vizsgálni

## 10. A szabályzat felülvizsgálata

A szabályzatot legalább évente felül kell vizsgálni, és szükség szerint frissíteni kell. A módosításokat az információbiztonsági felelősnek kell jóváhagynia.
