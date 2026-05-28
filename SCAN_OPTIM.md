# Optimisation vitesse spectrum sweep — TEF6686

## Problème identifié

Fichier : `TEF6686_arduino_F8605_CMB.ino`, fonction `scan()` ligne 903.

```cpp
Set_Cmd(scan_mode == 0 ? 32 : 33, 1, 2, 1, freq);
delay(10);  // ← coupable ligne 928
Get_Cmd(scan_mode == 0 ? 32 : 33, 128, uQuality, 4);
```

Sur bande FM Europe (87.5–108 MHz, pas 100 kHz = 206 fréquences) :
- 206 × 10 ms = ~2 s rien que pour les delays
- + transactions I²C à 100 kHz (défaut Arduino Nano)

---

## Leviers d'optimisation

### 1. Contrainte I²C à 400 kHz — délai 50 µs obligatoire (V205)

La doc V205 (§5.6) documente une contrainte absente du manuel V102 :
**50 µs minimum** entre la fin d'une transaction write et le début d'une transaction read.

Deux solutions :
- **Option A** : rester à ≤ 184 kHz — garantit le setup time sans délai supplémentaire
- **Option B** : passer à 400 kHz + ajouter `delayMicroseconds(27)` entre le stop write et le start read

```cpp
Wire.setClock(400000);
// entre Set_Cmd et Get_Cmd :
delayMicroseconds(27);  // garantit les 50 µs requis
```

> Sans ce délai à 400 kHz, les lectures peuvent retourner `0x0000` ou `0xFFF8` (erreur).

### 2. Réduction du delay(10)

Le `delay(10)` est empirique — aucune valeur minimale n'est documentée dans le manuel V102.

La doc V205 (§4.1.1) donne les éléments suivants pour calibrer :
- Un cycle **AF_Update complet** (mode=3) se termine en **6 ms** incluant mute/démute
- Le temps de mesure interne AF_Update est de **2 ms** (75% settling détecteur offset)
- Pour Search (mode=2) : pas de valeur chiffrée, mais le chip reste muté — les détecteurs
  n'ont pas besoin de converger complètement pour un sweep RSSI

Pour un sweep spectre (RSSI uniquement), tester par paliers :
```
10 ms → 7 ms → 5 ms → 3 ms → 2 ms
```
Valider que `uQuality[1]` (RSSI) est stable et cohérent à chaque palier.

### 3. Get_Quality_Status vs Get_Quality_Data (V205 uniquement)

En V205, deux commandes distinctes :
- **cmd 128 `Get_Quality_Status`** — retourne status + données, sans flush des données AF_Update
- **cmd 129 `Get_Quality_Data`** — retourne status + données, flush après lecture

Pour un sweep : utiliser **cmd 128** (déjà le cas dans le code actuel — correct).

### 4. Vitesse I²C (indépendant du délai)

Ajouter dans `setup()` :
```cpp
Wire.setClock(400000);
```
Le TEF668X supporte 400 kHz (User Manual V102 §2.1, V205 §5.6).
Réduction du temps de chaque transaction I²C, cumulable avec les autres optimisations.

---

## Baseline à mesurer avant toute modif

```cpp
uint32_t t0 = millis();
scan(false);
Serial.println(millis() - t0);
```

---

## Résumé des timings documentés (V205)

| Action | Timing documenté |
|--------|-----------------|
| Preset mute FM | ~32 ms |
| Preset mute AM | ~60 ms |
| Search/Preset mute slope | 10 ms (si mute inactif) / 0 ms (si déjà muté) |
| AF_Update cycle complet | 6 ms |
| AF_Update mesure qualité | 2 ms (75% settling offset) |
| Jump/Check/AF_Update mute slope | 1 ms |
| Check mute minimum (End) | ~16 ms |
| Changement de bande FM↔AM | +15 ms max |
| Délai read après write à 400 kHz | 50 µs min (27 µs délai suffit) |

---

## Notes
- User Manual V102 : `UserManual_TEF668X_V102.pdf`
- User Manual V205 : `UM_Radio_TEF668XA_V205-1.pdf`
- `uQuality[1]` = LEVEL (RSSI ×10, donc `/10` pour avoir dBµV)
- Mode 2 (Search) utilisé correctement — chip reste muté, pas de reset détecteurs entre chaque pas
- Les timings ci-dessus sont issus du manuel V205 ; le V102 ne documente pas ces valeurs
