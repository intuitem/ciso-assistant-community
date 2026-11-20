---
title: Kriptográfiai és titkosítási szabályzat
description: Szabványok a kriptográfiai kontrollok és a titkosítás alkalmazásához az információk védelmében
---

# Kriptográfiai és titkosítási szabályzat

## 1. Cél

Ez a szabályzat meghatározza a(z) [Szervezet neve] információinak bizalmasságát, integritását és hitelességét védő kriptográfiai kontrollok alkalmazására vonatkozó követelményeket.

## 2. Hatály

A szabályzat hatálya kiterjed a(z) [Szervezet neve] tulajdonában vagy kezelésében lévő minden rendszerre, alkalmazásra és adatra, beleértve a tárolt, a továbbított és a használatban lévő adatokat.

## 3. Titkosítási szabványok

### 3.1 Tárolt adatok

- A kiszolgálókon, adatbázisokban és adathordozókon tárolt minden érzékeny és bizalmas adatot titkosítani kell.
- Minden végponti eszközön (laptopok, munkaállomások, mobileszközök) be kell kapcsolni a teljes lemeztitkosítást.
- Jóváhagyott algoritmusok: AES-256 a szimmetrikus titkosításhoz.

### 3.2 Továbbított adatok

- Az érzékeny adatokat hordozó minden hálózati kommunikációhoz titkosított csatornát kell használni.
- Minden webes és API-kommunikációhoz TLS 1.2 vagy újabb verzió kötelező.
- Az elavult protokollok (SSL, TLS 1.0, TLS 1.1) használata tilos.
- A távoli hozzáféréshez használt VPN-kapcsolatoknak jóváhagyott titkosítási szabványokat kell alkalmazniuk.

### 3.3 Használatban lévő adatok

- Ahol ez műszakilag megvalósítható, az érzékeny adatok feldolgozásához ajánlott alkalmazásszintű titkosítást használni.
- A kiemelten érzékeny mezőkre (pl. hitelesítő adatok, pénzügyi adatok) ajánlott adatbázismező-szintű titkosítást alkalmazni.

## 4. Kulcskezelés

### 4.1 Kulcsok előállítása

- A kriptográfiai kulcsokat jóváhagyott véletlenszám-generátorokkal kell előállítani.
- A kulcshosszaknak el kell érniük vagy meg kell haladniuk az aktuális iparági ajánlásokban szereplő értékeket.

### 4.2 Kulcsok tárolása és védelme

- Magánkulcsot soha nem szabad nyílt szövegként tárolni.
- A kritikus kulcsokhoz ajánlott hardveres biztonsági modult (HSM) vagy azzal egyenértékű kulcskezelő szolgáltatást használni.
- A kriptográfiai kulcsokhoz való hozzáférést kizárólag a jogosult személyekre kell korlátozni.

### 4.3 Kulcsok cseréje és lejárata

- A titkosítási kulcsokat kockázatértékelésen alapuló, meghatározott ütemezés szerint kell cserélni.
- A kompromittálódott vagy feltehetően kompromittálódott kulcsokat azonnal vissza kell vonni, és újakkal kell pótolni.
- A lejárt kulcsokat a megőrzési követelményeknek megfelelően biztonságosan archiválni kell vagy meg kell semmisíteni.

### 4.4 Kulcsok megsemmisítése

- A már nem szükséges kulcsokat jóváhagyott módszerekkel, biztonságosan meg kell semmisíteni.
- A kulcsok megsemmisítését dokumentálni kell, és annak auditálhatónak kell lennie.

## 5. Tanúsítványkezelés

- A digitális tanúsítványokat megbízható hitelesítésszolgáltatóknak kell kiállítaniuk.
- A tanúsítványok lejáratát figyelemmel kell kísérni, a megújítást pedig a lejárat előtt el kell végezni.
- Éles környezetben az önaláírt tanúsítványok használata tilos.

## 6. Tiltott gyakorlatok

- Egyedi fejlesztésű vagy nem ellenőrzött titkosítási algoritmusok használata tilos.
- A titkosítási kulcsok beégetése a forráskódba tilos.
- A titkosítási kulcsok továbbítása titkosítatlan csatornán tilos.
- A titkosítási kontrollok letiltása vagy megkerülése dokumentált jóváhagyás nélkül tilos.

## 7. Szerepkörök és felelősségek

- **IT-biztonsági csapat**: a titkosítási szabványok meghatározása, a kulcsinfrastruktúra kezelése és a megfelelőségi felülvizsgálatok elvégzése.
- **Rendszergazdák**: a titkosítás bevezetése és fenntartása a rendszereken és az infrastruktúrán.
- **Fejlesztők**: a titkosítási szabványok követése az alkalmazásfejlesztésben és gondoskodás a kulcsok biztonságos kezeléséről.
- **Minden munkavállaló**: az adatok kezelésére és az eszközök használatára vonatkozó titkosítási követelmények betartása.

## 8. Megfelelőség

A szabályzat megszegése fegyelmi intézkedést vonhat maga után, amely a munkaviszony megszüntetéséig terjedhet. A meg nem felelés emellett jogi és szabályozói szankciókkal járhat a(z) [Szervezet neve] számára.

## 9. A szabályzat felülvizsgálata

A szabályzatot legalább évente, illetve a fenyegetési környezet, a technológiai környezet vagy a szabályozói követelmények jelentős változása esetén felül kell vizsgálni.
