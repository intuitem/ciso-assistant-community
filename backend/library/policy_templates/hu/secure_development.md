---
title: Biztonságos fejlesztési életciklus szabályzata
description: A szoftverfejlesztés, a tesztelés és a telepítés biztonsági követelményei
---

# Biztonságos fejlesztési életciklus szabályzata

## 1. Cél

Ez a szabályzat meghatározza a(z) [Szervezet neve] szoftverfejlesztési életciklusának egészébe beépítendő biztonsági követelményeket annak érdekében, hogy az alkalmazásokat és a rendszereket biztonságosan tervezzék, fejlesszék, teszteljék és telepítsék.

## 2. Hatály

A szabályzat hatálya kiterjed a(z) [Szervezet neve] minden szoftverfejlesztési tevékenységére, beleértve a belső fejlesztést, a kiszervezett fejlesztést, a kereskedelmi szoftverek testreszabását és a nyílt forráskódú projektekhez való hozzájárulást.

## 3. Biztonsági követelmények

- A biztonsági követelményeket minden projekt követelménymeghatározási szakaszában azonosítani és dokumentálni kell.
- A követelményeknek ki kell terjedniük a hitelesítésre, a jogosultságkezelésre, az adatok védelmére, a naplózásra és a bemeneti adatok ellenőrzésére.
- Az érzékeny adatokat kezelő vagy külső hálózatok felől elérhető alkalmazások esetében ajánlott fenyegetésmodellezést végezni.

## 4. Biztonságos kódolási szabványok

### 4.1 Általános elvek

- Minden fejlesztésnek elismert biztonságos kódolási irányelveket kell követnie (pl. OWASP Top 10, SANS Top 25).
- Minden, a felhasználótól származó adatot bemeneti ellenőrzésnek kell alávetni.
- A befecskendezéses (injection) támadások megelőzésére kimenetkódolást kell alkalmazni.
- Érzékeny adatokat (hitelesítő adatok, kulcsok, tokenek) soha nem szabad a forráskódba beégetni.

### 4.2 Függőségek kezelése

- A harmadik féltől származó programkönyvtárakat és függőségeket nyilvántartásba kell venni, és az ismert sérülékenységek szempontjából figyelemmel kell kísérni.
- A függőségeket rendszeresen frissíteni kell, és meghatározott verziókhoz kell rögzíteni.
- A nem karbantartott vagy elavult programkönyvtárak használata kerülendő.

### 4.3 Titkok kezelése

- Az alkalmazások titkait jóváhagyott titokkezelő megoldásokban kell tárolni.
- Titkokat nem szabad verziókezelő tárolókba véglegesíteni (commit).
- A titkok véletlen kiszivárgásának észlelésére ajánlott pre-commit hookokat vagy automatizált szkennelést használni.

## 5. Kódfelülvizsgálat

- Minden kódmódosítást társfejlesztői felülvizsgálatnak kell alávetni a fő ágakba való összevonás előtt.
- A hitelesítést, a jogosultságkezelést, az adatok kezelését és a kriptográfiát érintő módosításoknál biztonsági szempontú felülvizsgálatot kell végezni.
- A fejlesztési folyamatba ajánlott automatizált statikus kódelemző eszközöket beépíteni.

## 6. Tesztelés

### 6.1 Biztonsági tesztelés

- Az automatizált biztonsági tesztelést (SAST, DAST) be kell építeni a CI/CD-folyamatba.
- A magas kockázatú alkalmazásoknál a jelentős kiadások előtt manuális biztonsági tesztelést kell végezni.
- Az azonosított sérülékenységeket az éles telepítés előtt ki kell javítani.

### 6.2 Tesztkörnyezetek

- A tesztkörnyezetekben nem szabad éles adatokat tárolni, kivéve, ha azokat anonimizálták vagy maszkolták.
- A tesztkörnyezeteket el kell különíteni az éles rendszerektől.

## 7. Telepítés biztonsága

- Az éles telepítéseknek a kialakított változáskezelési folyamatot kell követniük.
- Az automatizált telepítési folyamatokba kötelező biztonsági kapukat kell beépíteni (sikeres tesztek, nincs kritikus sérülékenység).
- Minden éles telepítéshez visszaállítási (rollback) eljárást kell meghatározni és tesztelni.

## 8. Környezetek szétválasztása

- A fejlesztői, a teszt-, az átmeneti (staging) és az éles környezetet logikailag vagy fizikailag szét kell választani.
- Az éles környezetekhez való hozzáférést korlátozni és auditálni kell.
- A fejlesztőknek nem szabad közvetlen írási hozzáféréssel rendelkezniük az éles rendszerekhez.

## 9. Forráskód védelme

- A forráskódtárolókhoz való hozzáférést szerepköralapú jogosultságokkal kell szabályozni.
- A fő és a kiadási ágakon ágvédelmi szabályokat kell érvényesíteni.
- A tárolókhoz való hozzáférést időszakosan felül kell vizsgálni, a távozott munkatársakét pedig vissza kell vonni.

## 10. Szerepkörök és felelősségek

- **Fejlesztőcsapatok**: a biztonságos kódolási szabványok követése, a kódfelülvizsgálatok elvégzése és a sérülékenységek javítása.
- **IT-biztonsági csapat**: a biztonsági követelmények meghatározása, útmutatás nyújtása, biztonsági értékelések elvégzése és a biztonsági tesztelőeszközök kezelése.
- **Projektvezetők**: annak biztosítása, hogy a biztonsági tevékenységek szerepeljenek a projekttervekben és az ütemtervekben.
- **Minőségbiztosítás**: a biztonsági tesztesetek végrehajtása és az azonosított problémák javításának ellenőrzése.

## 11. Megfelelőség

A szabályzat megszegése a kód telepítésének letiltásával járhat. Az ismételt meg nem felelés fegyelmi intézkedést vonhat maga után.

## 12. A szabályzat felülvizsgálata

A szabályzatot legalább évente, illetve a fejlesztési gyakorlatok, az alkalmazott technológiák vagy a szabályozói követelmények jelentős változása esetén felül kell vizsgálni.
