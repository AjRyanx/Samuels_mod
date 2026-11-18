# Prompt for Gemini - rebuild `clubs.csv` (SP Football Life 2027 kit/sponsor mod)

## ROLE
You are a football data engineer. Produce a single CSV file named `clubs.csv`.

## WHY
This file feeds a Master-League mod that repaints a club's home/away/third kits with a
sponsor logo. The mod reads a club row by its **team id** and uses the colours to draw the
kit. **The current `clubs.csv` has invented, wrong team ids**, which makes teams collide and
get the wrong colours. Your job is to replace it with a complete, correct table.

## HARD RULES
1. **Use the team ids in the tables below EXACTLY.** They are read straight out of the game
   files and are the only correct ids. Never invent, renumber, or guess an id.
2. **One row per club team.** Skip national teams (they have no sponsor kit) - they are
   listed separately at the end only so you can recognise and ignore them.
3. Output **only** the CSV (optionally inside one ```csv fenced block). No prose, no notes.
4. Header line exactly: `team_id,name,primary,secondary,accent,tier`
5. Colours are `#RRGGBB` uppercase. `primary` = the shirt's main colour.
6. `tier` is exactly one of `big`, `mid`, `small` (see the tier guide).
7. Do **not** quote fields unless a name contains a comma; then wrap that name in double quotes.
8. No duplicate `team_id`. No blank lines. LF line endings.
9. Names: keep them short and ASCII (replace accents: `Nurnberg`, `Malaga`, `Beziers`).
   Use the name from the tables when a club is listed there.

## HOW TO CHOOSE THE THREE COLOURS
For every club:
- `primary`   = the club's main home-shirt colour.
- `secondary` = the second colour (shirt trim / shorts), ideally contrasting.
- `accent`    = a third colour for trim / details (never equal to primary or secondary).

**Source order (best first):**
1. If the club appears in **Table B (in-game kit colours)**, use those hex values directly:
   `primary = shirt1`, `secondary = shorts` (or `shirt2` if shorts equals shirt1),
   `accent = socks` (or `shirt2` if socks equals primary/secondary). Keep the hex as given.
2. Otherwise use the club's **real-world** home kit colours from your own knowledge
   (e.g. Manchester United red/white/black, Barcelona blue-garnet/gold, Juventus black/white).
3. If you truly do not know a club, pick a plausible colour and make `secondary`/`accent`
   contrast strongly with `primary`. Never leave a field empty.

## TIER GUIDE (drives the deal's money value)
- `big`   = elite / continental giants and the biggest clubs in a top league
- `mid`   = established top-division clubs
- `small` = lower-division, second-tier and minor-league clubs

## TABLE A - every club team and its correct team id
Format: `team_id | name | league`

```
100 | Manchester United | Premier League
101 | Arsenal | Premier League
102 | Chelsea | Premier League
103 | Liverpool | Premier League
104 | Leeds | Premier League
105 | West Ham | Premier League
106 | Newcastle | Premier League
107 | Aston Villa | Premier League
108 | Barcelona | LaLiga EA SPORTS
109 | Real Madrid | LaLiga EA SPORTS
110 | Valencia | LaLiga EA SPORTS
111 | La Coruna | LaLiga HYPERMOTION
112 | Monaco | Ligue 1
113 | Marseille | Ligue 1
114 | PSG | Ligue 1
115 | Bordeaux | Ligue 2
116 | Ajax | Eredivisie
117 | Feyenoord | Eredivisie
118 | PSV | Eredivisie
119 | Internazionale | Serie A Enilive
120 | Juventus | Serie A Enilive
121 | Milan | Serie A Enilive
122 | Lazio | Serie A Enilive
123 | Parma | Serie A Enilive
124 | Fiorentina | Serie A Enilive
125 | Roma | Serie A Enilive
126 | Dortmund | Bundesliga
127 | Munchen | Bundesliga
128 | Leverkusen | Bundesliga
129 | HSV | Bundesliga
130 | Galatasaray | Trendyol Super Lig
131 | Celtic | Scottish Premiership
132 | Rangers | Scottish Premiership
133 | Olympiakos Piraeus | Super League Greece
134 | Dynamo Kyiv | Other Europe
135 | Spartak Moskva | Russian Premier League
136 | Vasco da Gama | Brasileirao Assai - Serie A
137 | Palmeiras | Brasileirao Assai - Serie A
138 | River Plate | Liga Profesional de Futbol
139 | Boca Juniors | Liga Profesional de Futbol
144 | Hokkaido Consadole Sapporo | J1 League
146 | Kashima Antlers | J1 League
147 | Urawa Red Diamonds | J1 League
148 | Jef United Chiba | J1 League
149 | Kashiwa Reysol | J1 League
150 | FC Tokyo | J1 League
151 | Tokyo Verdy | J1 League
152 | Yokohama F Marinos | J1 League
153 | Shimizu S-Pulse | J1 League
155 | Nagoya Grampus | J1 League
156 | Kyoto Sanga | J1 League
157 | Gamba Osaka | J1 League
158 | Vissel Kobe | J1 League
159 | Sanfrecce Hiroshima | J1 League
161 | Mito Hollyhock | J1 League
163 | Kawasaki Frontale | J1 League
164 | Yokohama FC | J1 League
165 | Shonan Bellmare | J1 League
167 | Albirex Niigata | J1 League
168 | Cerezo Osaka | J1 League
169 | Avispa Fukuoka | J1 League
170 | Sagan Tosu | J1 League
172 | Atletico | LaLiga EA SPORTS
173 | Manchester City | Premier League
174 | Anderlecht | Jupiler Pro League
175 | Sparta Praha | Other Europe
176 | Blackburn | Sky Bet Championship
177 | Everton | Premier League
178 | Fulham | Premier League
179 | Tottenham | Premier League
180 | Auxerre | Ligue 1
181 | Lyon | Ligue 1
182 | Lens | Ligue 1
184 | Schalke | 2. Bundesliga
185 | Bremen | Bundesliga
186 | Bologna | Serie A Enilive
187 | Brescia | Serie BKT
190 | Udinese | Serie A Enilive
191 | Benfica | Liga Portugal Betclic
192 | Porto | Liga Portugal Betclic
193 | Sporting CP | Liga Portugal Betclic
194 | Betis | LaLiga EA SPORTS
195 | Celta | LaLiga EA SPORTS
196 | Real Sociedad | LaLiga EA SPORTS
197 | Fenerbahce | Trendyol Super Lig
198 | Panathinaikos | Super League Greece
201 | Birmingham City | Sky Bet Championship
203 | Charlton Athletic | Sky Bet Championship
204 | Leicester | Sky Bet Championship
205 | Middlesbrough | Sky Bet Championship
207 | Southampton | Sky Bet Championship
208 | Wolverhampton | Premier League
209 | Ajaccio | Ligue 2
210 | Bastia | Ligue 2
211 | Guingamp | Ligue 2
213 | Lille | Ligue 1
215 | Montpellier | Ligue 2
216 | Nantes | Ligue 1
217 | Nice | Ligue 1
218 | Rennes | Ligue 1
219 | Sochaux | Ligue 2
221 | Toulouse | Ligue 1
225 | Monchengladbach | Bundesliga
226 | Frankfurt | Bundesliga
227 | Freiburg | Bundesliga
228 | Hannover 96 | 2. Bundesliga
229 | Hansa Rostock | 2. Bundesliga
231 | Stuttgart | Bundesliga
232 | Wolfsburg | Bundesliga
234 | Atalanta | Serie A Enilive
235 | Empoli | Serie BKT
237 | Modena | Serie BKT
238 | Palermo | Serie BKT
239 | Reggina | Serie BKT
240 | Sampdoria | Serie BKT
242 | AZ | Eredivisie
244 | Groningen | Eredivisie
245 | Heerenveen | Eredivisie
246 | NAC Breda | Eredivisie
247 | NEC Nijmegen | Eredivisie
250 | Twente | Eredivisie
251 | Utrecht | Eredivisie
252 | Vitesse | Eredivisie
253 | Volendam | Eredivisie
254 | RKC Waalwijk | Eredivisie
255 | Willem | Eredivisie
256 | PEC | Eredivisie
258 | Athletic | LaLiga EA SPORTS
259 | Espanyol | LaLiga EA SPORTS
260 | Malaga | LaLiga HYPERMOTION
261 | Mallorca | LaLiga EA SPORTS
263 | Osasuna | LaLiga EA SPORTS
264 | Racing de Santander | LaLiga HYPERMOTION
265 | Sevilla | LaLiga EA SPORTS
266 | Real Valladolid | LaLiga HYPERMOTION
267 | Villarreal | LaLiga EA SPORTS
268 | Real Zaragoza | LaLiga HYPERMOTION
269 | Club Brugge | Jupiler Pro League
270 | AEK Athens | Super League Greece
271 | Lokomotiv Moskva | Russian Premier League
272 | Partizan | Other Europe
273 | Besiktas | Trendyol Super Lig
274 | Cruzeiro | Brasileirao Assai - Serie A
277 | Suwon Samsung Bluewings | AFC Champions League
281 | Pohang Steelers | K League
295 | Beijing FC | AFC Champions League
306 | Jiangsu Suning | Chinese Super League
310 | Guangzhou Evergrande | AFC Champions League
317 | Ascoli | Serie BKT
319 | Bari | Serie BKT
320 | Cagliari | Serie A Enilive
323 | Genoa | Serie A Enilive
327 | Napoli | Serie A Enilive
328 | Pescara | Serie BKT
331 | Ternana | Serie BKT
333 | Torino | Serie A Enilive
336 | Hellas Verona | Serie A Enilive
344 | Excelsior Rotterdam | Eredivisie
345 | Fortuna Sittard | Eredivisie
346 | Go Ahead Eagles | Eredivisie
349 | Heracles Almelo | Eredivisie
351 | Sparta Rotterdam | Eredivisie
352 | Telstar | Eredivisie
357 | Almeria | LaLiga HYPERMOTION
359 | Cordoba | LaLiga HYPERMOTION
361 | Elche | LaLiga EA SPORTS
362 | Getafe | LaLiga EA SPORTS
363 | Sporting de Gijón | LaLiga HYPERMOTION
364 | Las Palmas | LaLiga HYPERMOTION
366 | Levante | LaLiga EA SPORTS
370 | Rayo Vallecano | LaLiga EA SPORTS
377 | Brighton & Hove Albion | Premier League
378 | Burnley | Premier League
379 | Cardiff | Sky Bet Championship
382 | Crystal Palace | Premier League
383 | Derby County | Sky Bet Championship
386 | Ipswich | Sky Bet Championship
387 | Millwall | Sky Bet Championship
388 | Norwich | Sky Bet Championship
389 | Nottingham Forest | Premier League
394 | Sheffield Wednesday | Sky Bet Championship
395 | Stoke City | Sky Bet Championship
396 | Sunderland | Premier League
398 | Watford | Sky Bet Championship
399 | West Bromwich Albion | Sky Bet Championship
403 | Angers | Ligue 1
405 | Caen | Ligue 2
407 | Clermont | Ligue 2
412 | Laval | Ligue 2
413 | Havre | Ligue 1
414 | Lorient | Ligue 1
416 | Niort | Ligue 2
418 | Saint Etienne | Ligue 2
420 | Troyes | Ligue 2
431 | Fortuna Düsseldorf | 2. Bundesliga
436 | Mainz | Bundesliga
437 | Nürnberg | 2. Bundesliga
1195 | Genk | Jupiler Pro League
1196 | Gent | Jupiler Pro League
1197 | Standard Liege | Jupiler Pro League
1200 | Mechelen | Jupiler Pro League
1203 | Dinamo Zagreb | Other Europe
1206 | Slovan Liberec | Other Europe
1207 | Kobenhavn | 3F Superliga
1208 | Nordsjaelland | 3F Superliga
1212 | PAOK | Super League Greece
1213 | Maccabi Haifa | Other Europe
1215 | Rosenborg | Other Europe
1216 | FCSB | Other Europe
1217 | CSKA Moskva | Russian Premier League
1218 | Zenit | Russian Premier League
1219 | Aberdeen | Scottish Premiership
1220 | Dundee United | Scottish Premiership
1221 | Hearts | Scottish Premiership
1222 | Hibernian | Scottish Premiership
1223 | Crvena Zvezda | Other Europe
1226 | Djurgardens | Other Europe
1228 | Grasshoppers | Credit Suisse Super League
1230 | Gençlerbirliği | Trendyol Super Lig
1232 | Shakhtar Donetsk | Other Europe
1236 | Argentinos Juniors | Liga Profesional de Futbol
1237 | Racing Club | Liga Profesional de Futbol
1238 | Estudiantes | Liga Profesional de Futbol
1239 | Gimnasia La Plata | Liga Profesional de Futbol
1240 | Independiente | Liga Profesional de Futbol
1241 | Newells Old Boys | Liga Profesional de Futbol
1242 | Rosario Central | Liga Profesional de Futbol
1243 | San Lorenzo | Liga Profesional de Futbol
1244 | Velez Sarsfield | Liga Profesional de Futbol
1245 | Atletico Mineiro | Brasileirao Assai - Serie A
1246 | Botafogo | Brasileirao Assai - Serie A
1247 | Corinthians | Brasileirao Assai - Serie A
1248 | Flamengo | Brasileirao Assai - Serie A
1249 | Fluminense | Brasileirao Assai - Serie A
1250 | Gremio | Brasileirao Assai - Serie A
1251 | Guarani | Brasileirao SportingBet - Serie B
1252 | Internacional | Brasileirao Assai - Serie A
1254 | Santos | Brasileirao Assai - Serie A
1255 | Sao Paulo | Brasileirao Assai - Serie A
1256 | Colo Colo | Campeonato Itau
1257 | America de Cali | Liga Betplay Dimayor
1258 | Millonarios | Liga Betplay Dimayor
1260 | Cerro Porteno | Other America
1261 | Olimpia | Other America
1262 | Nacional de Football | Other America
1263 | Penarol | Other America
1264 | America | Other America
1327 | Queens Park Rangers | Sky Bet Championship
1328 | Dijon | Ligue 2
1329 | Brest | Ligue 1
1330 | Reims | Ligue 2
1348 | Al Shabab | Saudi Pro League
1349 | Al Ahli Saudi | Saudi Pro League
1350 | Ittihad Club | Saudi Pro League
1351 | Al Wehda | Saudi Pro League
1362 | Cesena | Serie BKT
1489 | Al Hilal | Saudi Pro League
1493 | Buriram United | AFC Champions League
1528 | Valenciennes | Ligue 2
1586 | Salzburg | Other Europe
1589 | Hull City | Sky Bet Championship
1598 | Almere City | Eredivisie
1600 | Spezia | Serie BKT
1699 | Pachuca | Other America
1702 | Malmo | Other Europe
1706 | Basel | Other Europe
1733 | HJK | Other Europe
1746 | Cluj | Other Europe
1753 | Dinamo Moskva | Russian Premier League
1756 | Legia Warszawa | Ekstraklasa
1760 | Bristol | Sky Bet Championship
1765 | Granada | LaLiga HYPERMOTION
1778 | Monterrey | Other America
1782 | Tigres | Other America
1789 | Leon | Other America
1804 | Vitória Guimarães | Liga Portugal Betclic
1809 | Sivasspor | Trendyol Super Lig
1818 | Aalborg | 3F Superliga
1819 | Rapid Wien | Other Europe
1832 | Brondby | 3F Superliga
1881 | Fagiano Okayama | J1 League
1902 | Ettifaq Club | Saudi Pro League
1907 | LDU Quito | Other America
1909 | Swansea | Sky Bet Championship
1910 | Nimes | Ligue 2
1919 | Sassuolo | Serie A Enilive
1920 | Cittadella | Serie BKT
1922 | Huracan | Liga Profesional de Futbol
1924 | Godoy Cruz | Liga Profesional de Futbol
1925 | San Martin | Liga Profesional de Futbol
1926 | Tigre | Liga Profesional de Futbol
1927 | Banfield | Liga Profesional de Futbol
1929 | Lanus | Liga Profesional de Futbol
1930 | Athletico Paranaense | Brasileirao Assai - Serie A
1931 | Coritiba | Brasileirao Assai - Serie A
1933 | Goias | Brasileirao SportingBet - Serie B
1935 | Clube Náutico Capibaribe | Brasileirao SportingBet - Serie B
1936 | Sport Recife | Brasileirao SportingBet - Serie B
1937 | Vitoria | Brasileirao Assai - Serie A
1941 | Rubin Kazan | Russian Premier League
1944 | CD Nacional | Liga Portugal Betclic
1945 | Trabzonspor | Trendyol Super Lig
1948 | Aris | Super League Greece
1950 | Young Boys | Other Europe
1955 | Sion | Credit Suisse Super League
1957 | Zurich | Credit Suisse Super League
1958 | Servette | Credit Suisse Super League
1974 | Sporting Braga | Liga Portugal Betclic
1979 | Rio Ave | Liga Portugal Betclic
1985 | Kilmarnock | Scottish Premiership
1986 | Motherwell | Scottish Premiership
1987 | St Mirren | Scottish Premiership
1989 | Antalyaspor | Trendyol Super Lig
1995 | Istanbul Basaksehir | Trendyol Super Lig
1996 | Kayserispor | Trendyol Super Lig
2008 | Zorya Luhansk | Other Europe
2009 | Cercle Brugge | Jupiler Pro League
2010 | Sporting Charleroi | Jupiler Pro League
2013 | Kortrijk | Jupiler Pro League
2016 | Dundalk | Other Europe
2019 | Zulte Waregem | Jupiler Pro League
2020 | Asteras Tripolis | Super League Greece
2024 | Levadiakos | Super League Greece
2025 | OFI Crete | Super League Greece
2037 | Viktoria Plzen | Other Europe
2058 | Kairat | Other Europe
2066 | Horsens | 3F Superliga
2067 | Aarhus | 3F Superliga
2069 | Midtjylland | 3F Superliga
2070 | Odense | 3F Superliga
2071 | Randers | 3F Superliga
2078 | LASK Linz | Other Europe
2081 | Sturm Graz | Other Europe
2101 | Maccabi Tel-Aviv | Other Europe
2125 | Górnik Zabrze | Ekstraklasa
2127 | Lech Poznan | Ekstraklasa
2131 | Piast Gliwice | Ekstraklasa
2178 | APOEL | Other Europe
2185 | Omonia | Other Europe
2187 | Girona | LaLiga EA SPORTS
2188 | Huesca | LaLiga HYPERMOTION
2191 | Universidad Catolica | Campeonato Itau
2192 | Audax Italiano | Campeonato Itau
2193 | Atletico Nacional | Liga Betplay Dimayor
2194 | Cúcuta Deportivo | Liga Betplay Dimayor
2195 | Boyaca Chico | Liga Betplay Dimayor
2198 | Libertad | Other America
2205 | Caracas | Other America
2208 | Everton | Campeonato Itau
2209 | Universidad de Chile | Campeonato Itau
2210 | Independiente Medellin | Liga Betplay Dimayor
2213 | Guarani | Other America
2215 | Universitario | Other America
2216 | Sporting Cristal | Other America
2218 | Tachira | Other America
2229 | Rostov | Russian Premier League
2283 | Bolivar | Other America
2284 | Once Caldas | Liga Betplay Dimayor
2285 | Junior | Liga Betplay Dimayor
2286 | Emelec | Other America
2287 | Alianza Lima | Other America
2320 | Padova | Serie BKT
2358 | Jorge Wilstermann | Other America
2360 | Union Espanola | Campeonato Itau
2361 | Deportes Tolima | Liga Betplay Dimayor
2363 | Liverpool | Other America
2365 | St Johnstone | Scottish Premiership
2369 | Portimonense | Liga Portugal Betclic
2372 | Machida Zelvia | J1 League
2373 | V-Varen Nagasaki | J1 League
2374 | Astana | Other Europe
2375 | Ferencvarosi | Other Europe
2380 | Arouca | Liga Portugal Betclic
2383 | Estoril | Liga Portugal Betclic
2387 | Gil Vicente | Liga Portugal Betclic
2388 | Moreirense | Liga Portugal Betclic
2391 | Santa Clara | Liga Portugal Betclic
2392 | Wolfsberger | Other Europe
2393 | Alcorcón | LaLiga HYPERMOTION
2450 | America Mineiro | Brasileirao SportingBet - Serie B
2451 | Atletico Goianiense | Brasileirao SportingBet - Serie B
2452 | Avai | Brasileirao SportingBet - Serie B
2453 | Bahia | Brasileirao Assai - Serie A
2454 | Ceara | Brasileirao SportingBet - Serie B
2459 | Red Bull Bragantino | Brasileirao Assai - Serie A
2460 | Criciuma | Brasileirao SportingBet - Serie B
2465 | Ponte Preta | Brasileirao SportingBet - Serie B
2468 | Vila Nova | Brasileirao SportingBet - Serie B
2502 | The Strongest | Other America
2506 | CRB | Brasileirao SportingBet - Serie B
2517 | Juve Stabia | Serie BKT
2525 | Hajduk Split | Other Europe
2526 | Rijeka | Other Europe
2531 | CSKA Sofia | Other Europe
2534 | Hapoel Beer Sheva | Other Europe
2536 | Club Atlético Belgrano | Liga Profesional de Futbol
2538 | Union Santa Fe | Liga Profesional de Futbol
2541 | O Higgins | Campeonato Itau
2543 | Deportes Iquique | Campeonato Itau
2544 | Deportes La Serena | Campeonato Itau
2545 | Huachipato | Campeonato Itau
2546 | Union La Calera | Campeonato Itau
2547 | Deportes Antofagasta | Campeonato Itau
2548 | Palestino | Campeonato Itau
2549 | Cobreloa | Campeonato Itau
2551 | Universidad de Concepción | Campeonato Itau
2553 | Cobresal | Campeonato Itau
2555 | Volos | Super League Greece
2556 | Panetolikos | Super League Greece
2559 | Atromitos | Super League Greece
2576 | Al Fateh | Saudi Pro League
2577 | Al Nassr | Saudi Pro League
2578 | Al Raed | Saudi Pro League
2580 | Al Taawoun | Saudi Pro League
2602 | Tractor FC | AFC Champions League
2610 | Huddersfield | Sky Bet Championship
2614 | Tondela | Liga Portugal Betclic
2616 | Mirandes | LaLiga HYPERMOTION
2618 | Krasnodar | Russian Premier League
2621 | Dundee | Scottish Premiership
2622 | Ross County | Scottish Premiership
2625 | Kasimpasa | Trendyol Super Lig
2650 | Deportivo Cali | Liga Betplay Dimayor
2651 | Deportivo Pasto | Liga Betplay Dimayor
2652 | Envigado | Liga Betplay Dimayor
2653 | Rionegro | Liga Betplay Dimayor
2654 | Internacional de Bogota | Liga Betplay Dimayor
2655 | Patriotas Boyaca | Liga Betplay Dimayor
2657 | Santa Fe | Liga Betplay Dimayor
2658 | Barcelona SC | Other America
2659 | Independiente del Valle | Other America
2676 | Sport Boys | Other America
2699 | Nublense | Campeonato Itau
2707 | Coquimbo | Campeonato Itau
2708 | Curico Unido | Campeonato Itau
2709 | Deportes Concepción | Campeonato Itau
2710 | Deportes Copiapo | Campeonato Itau
2712 | CD Magallanes | Campeonato Itau
2717 | Aldosivi | Liga Profesional de Futbol
2719 | Atletico Tucuman | Liga Profesional de Futbol
2722 | Defensa y Justicia | Liga Profesional de Futbol
2726 | Rivadavia | Liga Profesional de Futbol
2727 | Instituto | Liga Profesional de Futbol
2730 | Sarmiento | Liga Profesional de Futbol
4071 | Bournemouth | Premier League
4074 | Eintracht Braunschweig | 2. Bundesliga
4085 | Chaves | Liga Portugal Betclic
4086 | SC Farense | Liga Portugal Betclic
4092 | Dalian Pro | Chinese Super League
4094 | Shanghai SIPG | AFC Champions League
4095 | Wuhan Zall | Chinese Super League
4108 | Chapecoense | Brasileirao Assai - Serie A
4123 | Metz | Ligue 1
4124 | Augsburg | Bundesliga
4125 | Hertha BSC | 2. Bundesliga
4126 | Hoffenheim | Bundesliga
4127 | Arminia Bielefeld | 2. Bundesliga
4128 | Bochum | 2. Bundesliga
4129 | Dynamo Dresden | 2. Bundesliga
4133 | Greuther Fürth | 2. Bundesliga
4135 | Kaiserslautern | 2. Bundesliga
4136 | Karlsruher | 2. Bundesliga
4137 | Koln | Bundesliga
4138 | 1860 München | 2. Bundesliga
4139 | St Pauli | Bundesliga
4140 | Union Berlin | Bundesliga
4141 | Avellino | Serie BKT
4143 | Krylia Sovetov Samara | Russian Premier League
4145 | Alaves | LaLiga EA SPORTS
4146 | Eibar | LaLiga HYPERMOTION
4147 | Tenerife | LaLiga HYPERMOTION
4148 | Chicago Fire | Major League Soccer
4150 | Colorado Rapids | Major League Soccer
4151 | Columbus Crew | Major League Soccer
4152 | DC United | Major League Soccer
4153 | FC Dallas | Major League Soccer
4154 | Houston Dynamo | Major League Soccer
4155 | LA Galaxy | Major League Soccer
4156 | CF Montreal | Major League Soccer
4157 | New England Revolution | Major League Soccer
4158 | New York Red Bulls | Major League Soccer
4159 | Philadelphia Union | Major League Soccer
4160 | Portland Timbers | Major League Soccer
4161 | Real Salt Lake | Major League Soccer
4162 | San Jose Earthquakes | Major League Soccer
4163 | Seattle Sounders | Major League Soccer
4164 | Sporting Kansas City | Major League Soccer
4165 | Toronto FC | Major League Soccer
4166 | Vancouver Whitecaps | Major League Soccer
4168 | Shandong Luneng Taishan | AFC Champions League
4178 | Nasaf | AFC Champions League
4180 | Brentford | Premier League
4183 | Coventry | Sky Bet Championship
4192 | Preston North End | Sky Bet Championship
4193 | Rotherham | Sky Bet Championship
4194 | Sheffield United | Sky Bet Championship
4200 | Amiens | Ligue 2
4206 | Dunkerque | Ligue 2
4211 | Paris | Ligue 1
4212 | Red Star | Ligue 2
4213 | Strasbourg | Ligue 1
4218 | Carrarese | Serie BKT
4219 | Como | Serie A Enilive
4220 | Cremonese | Serie A Enilive
4221 | Feralpisalò | Serie BKT
4225 | Reggiana | Serie BKT
4228 | Sudtirol | Serie BKT
4229 | Venezia | Serie BKT
4230 | Virtus Entella | Serie BKT
4233 | Catanzaro | Serie BKT
4234 | Frosinone | Serie BKT
4237 | Lecce | Serie A Enilive
4241 | Pisa | Serie A Enilive
4244 | Salernitana | Serie BKT
4247 | Burgos | LaLiga HYPERMOTION
4252 | Leonesa | LaLiga HYPERMOTION
4259 | Racing Ferrol | LaLiga HYPERMOTION
4260 | Real Oviedo | LaLiga EA SPORTS
4264 | Amorebieta | LaLiga HYPERMOTION
4272 | Leganes | LaLiga HYPERMOTION
4276 | Real Sociedad B | LaLiga HYPERMOTION
4301 | Villarreal B | LaLiga HYPERMOTION
4302 | Albacete | LaLiga HYPERMOTION
4308 | Cadiz | LaLiga HYPERMOTION
4309 | Cartagena | LaLiga HYPERMOTION
4323 | Boavista | Liga Portugal Betclic
4324 | Paderborn | 2. Bundesliga
4326 | Qarabag | Other Europe
4344 | Slovan Bratislava | Other Europe
4347 | Sheriff | Other Europe
4355 | Ludogorets | Other Europe
4363 | Luton | Sky Bet Championship
4364 | Plymouth Argyle | Sky Bet Championship
4365 | Portsmouth | Sky Bet Championship
4370 | Grenoble | Ligue 2
4372 | Rodez | Ligue 2
4379 | Mantova | Serie BKT
4395 | Castellon | LaLiga HYPERMOTION
4914 | Monza | Serie BKT
4928 | Cosenza | Serie BKT
4937 | St Gallen | Credit Suisse Super League
4943 | Guangzhou R&F | Chinese Super League
4959 | Paysandu | Brasileirao SportingBet - Serie B
4962 | Luzern | Credit Suisse Super League
4964 | Lausanne | Other Europe
4965 | Lugano | Other Europe
4968 | Winterthur | Credit Suisse Super League
4988 | Eldense | LaLiga HYPERMOTION
4995 | Central Cordoba | Liga Profesional de Futbol
4997 | Gimnasia Y Esgrima De Mendoza | Liga Profesional de Futbol
5008 | Darmstadt | 2. Bundesliga
5009 | Heidenheim | Bundesliga
5010 | Leipzig | Bundesliga
5015 | Carabobo | Other America
5028 | Famalicão | Liga Portugal Betclic
5046 | Talleres de Cordoba | Liga Profesional de Futbol
5048 | Londrina EC | Brasileirao SportingBet - Serie B
5061 | New York City FC | Major League Soccer
5062 | Orlando City | Major League Soccer
5086 | Oxford | Sky Bet Championship
5097 | Concarneau | Ligue 2
5099 | Pau | Ligue 2
5100 | Quevilly | Ligue 2
5115 | Vizela | Liga Portugal Betclic
5135 | Jeju SK | K League
5137 | Juventude | Brasileirao SportingBet - Serie B
5139 | Botafogo SP | Brasileirao SportingBet - Serie B
5142 | Cuiaba | Brasileirao SportingBet - Serie B
5143 | Fortaleza | Brasileirao SportingBet - Serie B
5145 | Remo | Brasileirao Assai - Serie A
5148 | Volta Redonda | Brasileirao SportingBet - Serie B
5168 | Chongqing Dangdai Lifan | Chinese Super League
5170 | Hebei China Fortune | Chinese Super League
5171 | Henan Jianye | Chinese Super League
5173 | Shanghai Shenhua | AFC Champions League
5175 | Tianjin Teda | Chinese Super League
5183 | Qingdao Huanghai | Chinese Super League
5184 | Shenzhen Kaisa | Chinese Super League
5185 | Shijiazhuang Everbright | Chinese Super League
5189 | Slavia Praha | Other Europe
5190 | KAS Eupen | Jupiler Pro League
5191 | Antwerp | Jupiler Pro League
5192 | Oostende | Jupiler Pro League
5194 | Sint Truiden | Jupiler Pro League
5196 | Akhmat Grozny | Russian Premier League
5197 | Arsenal Tula | Russian Premier League
5200 | Ufa | Russian Premier League
5201 | Ural | Russian Premier League
5202 | Alanyaspor | Trendyol Super Lig
5203 | Goztepe | Trendyol Super Lig
5204 | Konyaspor | Trendyol Super Lig
5207 | Alianza Petrolera | Liga Betplay Dimayor
5208 | Atletico Bucaramanga | Liga Betplay Dimayor
5209 | Cortulua | Liga Betplay Dimayor
5210 | Jaguares de Cordoba | Liga Betplay Dimayor
5216 | Beerschot | Jupiler Pro League
5217 | Leuven | Jupiler Pro League
5220 | Union SG | Jupiler Pro League
5221 | Westerlo | Jupiler Pro League
5224 | Lyngby | 3F Superliga
5225 | Silkeborg | 3F Superliga
5226 | Sonderjyske | 3F Superliga
5229 | Fredericia | 3F Superliga
5235 | Vejle | 3F Superliga
5237 | Viborg | 3F Superliga
5242 | Molde | Other Europe
5253 | FK Bodo Glimt | Other Europe
5266 | Arka Gdynia | Ekstraklasa
5267 | Termalica Nieciecza | Ekstraklasa
5268 | KS Cracovia | Ekstraklasa
5269 | Jagiellonia Białystok | Ekstraklasa
5270 | Korona Kielce | Ekstraklasa
5271 | Lechia Gdańsk | Ekstraklasa
5272 | Pogoń Szczecin | Ekstraklasa
5274 | Wisła Płock | Ekstraklasa
5275 | Zagłębie Lubin | Ekstraklasa
5279 | GKS Katowice | Ekstraklasa
5288 | Rakow | Ekstraklasa
5295 | Baltika | Russian Premier League
5296 | Sochi | Russian Premier League
5297 | Fakel Voronezh | Russian Premier League
5298 | Khimki | Russian Premier League
5300 | Nizhny Novgorod | Russian Premier League
5301 | Orenburg | Russian Premier League
5317 | Falkirk | Scottish Premiership
5319 | Livingston | Scottish Premiership
5322 | Hacken | Other Europe
5348 | Adana Demirspor | Trendyol Super Lig
5354 | Rizespor | Trendyol Super Lig
5356 | Gaziantep | Trendyol Super Lig
5357 | Giresunspor | Trendyol Super Lig
5358 | Istanbulspor | Trendyol Super Lig
5360 | Ankaragucu | Trendyol Super Lig
5361 | Samsunspor | Trendyol Super Lig
5366 | Riestra | Liga Profesional de Futbol
5370 | Deportivo Pereira | Liga Betplay Dimayor
5371 | Fortaleza CEIF | Liga Betplay Dimayor
5373 | Llaneros | Liga Betplay Dimayor
5376 | Union Magdalena | Liga Betplay Dimayor
5394 | Bangkok United | AFC Champions League
5395 | Chiangrai United | AFC Champions League
5423 | Hvidovre | 3F Superliga
5433 | Operario PR | Brasileirao SportingBet - Serie B
5452 | Hatayspor | Trendyol Super Lig
5454 | Platense | Liga Profesional de Futbol
5599 | Istiklol | AFC Champions League
5628 | Lecco | Serie BKT
5633 | Casa Pia | Liga Portugal Betclic
5636 | Torpedo Moskva | Russian Premier League
5644 | Andorra | LaLiga HYPERMOTION
5652 | Fatih Karagumruk | Trendyol Super Lig
5657 | Barracas | Liga Profesional de Futbol
5659 | Estudiantes De Río Cuarto | Liga Profesional de Futbol
5660 | Brusque | Brasileirao SportingBet - Serie B
5661 | Ituano | Brasileirao SportingBet - Serie B
5664 | Perth Glory | AFC Champions League
5669 | Shahr Khodrou | AFC Champions League
5683 | RWDM Molenbeek | Jupiler Pro League
5684 | Seraing | Jupiler Pro League
5685 | Annecy | Ligue 2
5719 | Holstein Kiel | 2. Bundesliga
5736 | Atlanta United | Major League Soccer
5737 | FC Cincinnati | Major League Soccer
5738 | Inter Miami | Major League Soccer
5739 | Nashville SC | Major League Soccer
5740 | Austin FC | Major League Soccer
5741 | Los Angeles FC | Major League Soccer
5742 | Minnesota United | Major League Soccer
5767 | Mirassol | Brasileirao Assai - Serie A
5768 | Novorizontino | Brasileirao SportingBet - Serie B
5819 | Yverdon Sport | Credit Suisse Super League
5820 | Eyupspor | Trendyol Super Lig
5821 | Kocaelispor | Trendyol Super Lig
5832 | Charlotte FC | Major League Soccer
5844 | CF Estrela Amadora | Liga Portugal Betclic
5845 | Alverca | Liga Portugal Betclic
5878 | Dender | Jupiler Pro League
5884 | Martigues | Ligue 2
5895 | Ceuta | LaLiga HYPERMOTION
5898 | Bodrumspor | Trendyol Super Lig
5899 | Pendikspor | Trendyol Super Lig
5903 | St. Louis | Major League Soccer
5909 | Amazonas | Brasileirao SportingBet - Serie B
5911 | São Bernardo | Brasileirao SportingBet - Serie B
5912 | Daejeon | K League
5913 | Gangwon | K League
5914 | Gwangju | K League
5915 | Incheon United | K League
5918 | Bucheon | K League
5923 | Anyang | K League
5924 | Gimcheon Sangmu | K League
5940 | Al Fayha | Saudi Pro League
5954 | AVS | Liga Portugal Betclic
5973 | Athletic Club | Brasileirao SportingBet - Serie B
5974 | Ferroviária De Esportes | Brasileirao SportingBet - Serie B
5980 | Deportes Limache | Campeonato Itau
6001 | Esperance | Other Africa
6006 | Al Ahly | Other Africa
6007 | Always Ready | Other America
6067 | RAAL | Jupiler Pro League
6069 | Wrexham | Sky Bet Championship
6084 | San Diego | Major League Soccer
6094 | Elversberg | 2. Bundesliga
9001 | Abha | Saudi Pro League
9002 | Al Riyadh | Saudi Pro League
9003 | Damac | Saudi Pro League
9004 | NEOM | Saudi Pro League
9005 | Al Okhdood | Saudi Pro League
9007 | Al Khaleej | Saudi Pro League
9008 | AE Larissa | Super League Greece
9010 | Al Kholood | Saudi Pro League
9012 | Al Qadsiah | Saudi Pro League
9013 | Al Orobah | Saudi Pro League
9015 | Dinamo Makhachkala | Russian Premier League
9016 | Akron | Russian Premier League
9019 | Panserraikos | Super League Greece
9020 | Kifisia | Super League Greece
9030 | Wydad Athletic Club | Other Africa
9500 | Preußen Münster | 2. Bundesliga
9501 | Jahn Regensburg | 2. Bundesliga
9502 | Magdeburg | 2. Bundesliga
9503 | Saarbrücken | 2. Bundesliga
9504 | Pafos | Other Europe
9505 | Widzew Łódź | Ekstraklasa
9506 | Radomiak Radom | Ekstraklasa
9507 | Motor Lublin | Ekstraklasa
65815 | Jeonbuk Hyundai Motors | K League
65818 | Seoul | K League
66871 | Al Ain | AFC Champions League
66877 | Sepahan | AFC Champions League
66895 | Pakhtakor | AFC Champions League
67112 | Esteghlal | AFC Champions League
67114 | Sydney | AFC Champions League
68103 | Al Duhail | AFC Champions League
69703 | Melbourne Victory | AFC Champions League
69706 | Al Shorta | AFC Champions League
69709 | Al Sadd | AFC Champions League
69710 | Ulsan Hyundai | K League
69712 | Shabab Al Ahli Dubai | AFC Champions League
70484 | Johor Darul Tazim | AFC Champions League
70487 | Persepolis | AFC Champions League
70489 | Al Wahda | AFC Champions League
71212 | Sharjah | AFC Champions League
```

## TABLE B - real in-game kit colours already extracted from the game files
Use these verbatim when the id appears here (they override your own knowledge).
Ids that appear in Table A but NOT here have no in-game kit file, so use your own
knowledge of that club's real colours.
Format: `team_id | name | shirt1 | shirt2 | shorts | socks`

```
1203 | Dinamo Zagreb | #0b416e | #0b416e | #0b416e | #FFFFFF
2525 | Hajduk Split | #E4d8d8 | #d8d8d8 | #2c2aa4 | #2c2aa4
71581 | HNK Gorica | #ffffff | #101010 | #ffffff | #ffffff
71582 | HNK Rijeka | #d8d8d8 | #64aace | #d8d8d8 | #d8d8d8
71583 | NK Istra 1961 | #dee641 | #4aa46a | #dee641 | #dee641
71584 | NK Lokomotiva Zagreb | #315ac5 | #ffffff | #315ac5 | #315ac5
71585 | NK Osijek | #ba1b06 | #ba1b06 | #ba1b06 | #ba1b06
71586 | NK Rudeš | #315ac5 | #ffffff | #315ac5 | #315ac5
71588 | NK Slaven Belupo | #2952b4 | #ffffff | #2952b4 | #2952b4
71589 | NK Varaždin | #3962d5 | #060502 | #3962d5 | #3962d5
71590 | Aalesunds FK | #ff6a20 | #ae7b4b | #ff6a20 | #ff6a20
71591 | Fredrikstad FK | #ffffff | #de1820 | #ffffff | #ffffff
71592 | Hamarkameratene | #ffffff | #009c62 | #ffffff | #ffffff
71593 | IK Start | #ffee29 | #f6e620 | #ffee29 | #ffee29
71594 | KFUM-Kameratene Oslo | #ffffff | #cd1018 | #ffffff | #ffffff
71595 | Kristiansund BK | #002994 | #202031 | #002994 | #002994
71596 | Lillestrøm SK | #080808 | #ffd500 | #080808 | #080808
71598 | Rosenborg BK | #ffffff | #080808 | #ffffff | #ffffff
71599 | Sandefjord Fotball | #0052bd | #1d58a7 | #0052bd | #0052bd
71600 | Sarpsborg 08 FF | #103183 | #ffffff | #103183 | #103183
71601 | SK Brann | #cd1018 | #cd0e16 | #cd1018 | #cd1018
71602 | Tromsø IL | #ffffff | #e60000 | #ffffff | #ffffff
71603 | Vålerenga Fotball | #0052bd | #cd1018 | #0052bd | #0052bd
71604 | Bukovyna Chernivtsi | #fff600 | #958700 | #fff600 | #fff600
71606 | Chornomorets Odesa | #005ac5 | #080808 | #005ac5 | #005ac5
71607 | Epicentr | #520052 | #ff00ff | #520052 | #520052
71608 | FC Kharkiv | #38081c | #d29406 | #38081c | #38081c
71609 | Karpaty Lviv | #ffffff | #008331 | #ffffff | #ffffff
71610 | Kolos Kovalivka | #ffffff | #080808 | #ffffff | #ffffff
71611 | Kryvbas Kryvyi Rih | #ffffff | #e60000 | #ffffff | #ffffff
71612 | Kudrivka | #3962e6 | #ffffff | #3962e6 | #3962e6
71613 | Livyi Bereh Kyiv | #ffd500 | #fff600 | #ffd500 | #ffd500
71614 | LNZ Cherkasy | #410073 | #f6f3f7 | #410073 | #410073
71615 | NC Veres Rivne | #080808 | #e60000 | #080808 | #080808
71616 | Obolon Kyiv | #008331 | #006231 | #008331 | #008331
71618 | Polissia Zhytomyr | #298b5a | #314152 | #298b5a | #298b5a
71619 | Zoria Luhansk | #e6e6e6 | #ffffff | #e6e6e6 | #e6e6e6
71621 | Leicester City | #104abd | #ffffff | #104abd | #104abd
71622 | Oxford United | #101831 | #ffcd00 | #101831 | #101831
71623 | Sheffield Wednesday | #ffffff | #0031a4 | #ffffff | #ffffff
71624 | Amiens SC | #ffffff | #080808 | #ffffff | #ffffff
71625 | SC Bastia | #0052d5 | #ffffff | #0052d5 | #0052d5
71626 | Stade Malherbe Caen | #0052d5 | #e60000 | #0052d5 | #0052d5
71627 | Valenciennes FC | #e60000 | #ffffff | #e60000 | #e60000
71628 | 1. FC Heidenheim 1846 | #bd4a31 | #202031 | #bd4a31 | #bd4a31
71629 | FC St. Pauli | #ffffff | #5a4139 | #ffffff | #ffffff
71630 | VfL Wolfsburg | #105231 | #084a21 | #105231 | #105231
71631 | AC Reggiana 1919 | #733141 | #2952b4 | #733141 | #733141
71632 | Delfino Pescara | #208bcd | #00395a | #208bcd | #208bcd
71633 | Spezia Calcio | #ffffff | #080808 | #ffffff | #ffffff
71634 | FC Volendam | #ee5a08 | #ffffff | #ee5a08 | #ee5a08
71635 | Heracles Almelo | #ffffff | #080808 | #ffffff | #ffffff
71636 | NAC Breda | #ffde00 | #080808 | #ffde00 | #ffde00
71637 | Livingston | #e6b44a | #080808 | #e6b44a | #e6b44a
71638 | Huesca | #18316a | #d52020 | #18316a | #18316a
71639 | Zaragoza | #ffffff | #73bdf6 | #ffffff | #ffffff
71640 | Antalyaspor | #f6f6f6 | #cd1018 | #f6f6f6 | #f6f6f6
71641 | Fatih Karagümrük A.Ş | #101010 | #a51820 | #101010 | #101010
71642 | Kayserispor | #b42031 | #e6de00 | #b42031 | #b42031
71643 | AFC Wimbledon | #00397b | #e6bd4a | #00397b | #00397b
71644 | Barnsley | #ee0020 | #5a1831 | #ee0020 | #ee0020
71645 | Blackpool | #f66220 | #ffffff | #f66220 | #f66220
71646 | Bradford City | #6a2039 | #080808 | #6a2039 | #6a2039
71647 | Bromley | #080808 | #ffffff | #080808 | #080808
71648 | Burton Albion | #ffc520 | #eeeeee | #ffc520 | #ffc520
71649 | Cambridge United | #ffa400 | #080808 | #ffa400 | #ffa400
71650 | Doncaster Rovers | #102041 | #d5092a | #102041 | #102041
71651 | Huddersfield Town | #ffffff | #0073b4 | #ffffff | #ffffff
71652 | Leyton Orient | #e60020 | #080808 | #e60020 | #e60020
71653 | Luton Town | #081829 | #d53118 | #081829 | #081829
71654 | Mansfield Town | #ffd541 | #083973 | #ffd541 | #ffd541
71655 | Milton Keynes Dons | #ffffff | #aaaaaa | #ffffff | #ffffff
71656 | Notts County | #ffffff | #080808 | #ffffff | #ffffff
71657 | Peterborough United | #0052b4 | #303040 | #0052b4 | #0052b4
71658 | Plymouth Argyle | #204139 | #ffffff | #204139 | #204139
71659 | Reading | #295abd | #ffffff | #295abd | #295abd
71660 | Stevenage | #cd1029 | #ffffff | #cd1029 | #cd1029
71661 | Stockport County | #0052b4 | #292941 | #0052b4 | #0052b4
71662 | Wigan Athletic | #084183 | #ffffff | #084183 | #084183
71663 | Wycombe Wanderers | #002041 | #ffffff | #002041 | #002041
71664 | Accrington Stanley | #ffffff | #d5394a | #ffffff | #ffffff
71665 | Barnet | #f68331 | #080808 | #f68331 | #f68331
71666 | Bristol Rovers | #0031a4 | #ffffff | #0031a4 | #0031a4
71667 | Cheltenham Town | #e61820 | #080808 | #e61820 | #e61820
71668 | Chesterfield | #20397b | #ffffff | #20397b | #20397b
71669 | Colchester United | #ffffff | #ffd562 | #ffffff | #ffffff
71670 | Crawley Town | #de1829 | #ffffff | #de1829 | #de1829
71671 | Crewe Alexandra | #ee3139 | #ffffff | #ee3139 | #ee3139
71672 | Exeter City | #b40018 | #080808 | #b40018 | #b40018
71673 | Fleetwood Town | #de1810 | #ffffff | #de1810 | #de1810
71674 | Gillingham | #0062b4 | #103983 | #0062b4 | #0062b4
71675 | Grimsby Town | #080808 | #e60000 | #080808 | #080808
71676 | Newport County | #080808 | #ffac31 | #080808 | #080808
71677 | Northampton Town | #732031 | #ffffff | #732031 | #732031
71678 | Oldham Athletic | #20318b | #ffffff | #20318b | #20318b
71679 | Port Vale | #e6ded5 | #080808 | #e6ded5 | #e6ded5
71680 | Rochdale | #1852a4 | #080603 | #1852a4 | #1852a4
71681 | Rotherham United | #ffffff | #cd1829 | #ffffff | #ffffff
71682 | Salford City | #e6d5a4 | #b43141 | #e6d5a4 | #e6d5a4
71683 | Shrewsbury Town | #2962c5 | #f6a441 | #2962c5 | #2962c5
71684 | Swindon Town | #ac0000 | #ffffff | #ac0000 | #ac0000
71685 | Tranmere Rovers | #ffffff | #20399c | #ffffff | #ffffff
71686 | Walsall | #e61831 | #ffffff | #e61831 | #e61831
71687 | York City | #de2029 | #ffffff | #de2029 | #de2029
71688 | AS Cannes | #ffffff | #e60000 | #ffffff | #ffffff
71689 | Bourg en Bresse 01 | #0052d5 | #ffffff | #0052d5 | #0052d5
71690 | FC Versailles | #2952b4 | #ffffff | #2952b4 | #2952b4
71691 | FC Villefranche | #0052d5 | #ffffff | #0052d5 | #0052d5
71692 | Football Club Fleury 91 | #ffffff | #080808 | #ffffff | #ffffff
71693 | Football Club Rouen 1899 | #e60000 | #ffffff | #e60000 | #e60000
71695 | Paris 13 Atlético | #080808 | #414141 | #080808 | #080808
71696 | Quevilly-Rouen Metropole | #ffd500 | #e60000 | #ffd500 | #ffd500
71697 | SC Aubagne Air Bel | #002062 | #fff600 | #002062 | #002062
71698 | US Concarneau | #0052d5 | #ffffff | #0052d5 | #0052d5
71699 | US Orléans | #fff600 | #fffc00 | #fff600 | #fff600
71700 | US Thionville Lusitanos | #737394 | #acaccd | #737394 | #737394
71701 | Vendée FC La Roche | #d52020 | #ffffff | #d52020 | #d52020
71702 | 1. FC Kaiserslautern | #d52029 | #ffffff | #d52029 | #d52029
71703 | 1. FC Magdeburg | #ffffff | #00529c | #ffffff | #ffffff
71704 | 1. FC Nürnberg | #5a2031 | #ffffff | #5a2031 | #5a2031
71705 | DSC Arminia Bielefeld | #18396a | #ffffff | #18396a | #18396a
71706 | Eintracht Braunschweig | #f6c500 | #0a4f8f | #f6c500 | #f6c500
71707 | FC Energie Cottbus | #cd0031 | #ffffff | #cd0031 | #cd0031
71708 | Hannover 96 | #d53139 | #080808 | #d53139 | #d53139
71709 | Hertha BSC | #202941 | #ffffff | #202941 | #202941
71710 | Holstein Kiel | #10418b | #b49441 | #10418b | #10418b
71711 | Karlsruher SC | #10418b | #103961 | #10418b | #10418b
71712 | SG Dynamo Dresden | #ffc539 | #080808 | #ffc539 | #ffc539
71713 | SpVgg Greuther Fürth | #ffffff | #5a9c6a | #ffffff | #ffffff
71714 | SV Darmstadt 98 | #085aac | #ffffff | #085aac | #085aac
71715 | VfL Bochum 1848 | #202941 | #ffffff | #202941 | #202941
71716 | VfL Osnabrück | #523194 | #834194 | #523194 | #523194
71717 | 1. FC Saarbrücken | #081018 | #fff600 | #081018 | #081018
71718 | F.C. Hansa Rostock | #0073bd | #ffffff | #0073bd | #0073bd
71719 | FC Ingolstadt 04 | #e60000 | #080808 | #e60000 | #e60000
71720 | FC Viktoria Köln 1904 | #080808 | #cd2031 | #080808 | #080808
71721 | FC Würzburger Kickers | #e60000 | #ffffff | #e60000 | #e60000
71722 | Fortuna Düsseldorf 1895 | #7b2939 | #ffffff | #7b2939 | #7b2939
71723 | MSV Duisburg | #0052bd | #ffffff | #0052bd | #0052bd
71724 | Rot-Weiss Essen | #ffffff | #c51829 | #ffffff | #ffffff
71725 | SC Fortuna Köln | #ffffff | #e60000 | #ffffff | #ffffff
71726 | SC Preußen Münster | #08524a | #ffffff | #08524a | #08524a
71727 | SG Sonnenhof Großaspach | #cd0020 | #ffffff | #cd0020 | #cd0020
71728 | Sportclub Verl | #ffffff | #000000 | #ffffff | #ffffff
71729 | SSV Jahn Regensburg | #ffffff | #b40000 | #ffffff | #ffffff
71730 | SV Meppen | #3962d5 | #ffffff | #3962d5 | #3962d5
71731 | SV Waldhof Mannheim 07 | #186294 | #080808 | #186294 | #186294
71732 | SV Wehen Wiesbaden | #080808 | #ee2031 | #080808 | #080808
71733 | TSG Hoffenheim II | #293141 | #2062a4 | #293141 | #293141
71734 | TSV Alemannia Aachen | #fff639 | #080808 | #fff639 | #fff639
71735 | TSV Havelse 1912 | #cd0020 | #e60000 | #cd0020 | #cd0020
71736 | VfB Stuttgart II | #ffffff | #e60000 | #ffffff | #ffffff
71737 | Atalanta Under 23 | #181818 | #206ab4 | #181818 | #181818
71738 | Campobasso Football Club | #10295a | #ffffff | #10295a | #10295a
71739 | Forlì | #ffffff | #cd1829 | #ffffff | #ffffff
71740 | Grosseto 1912 | #cd0020 | #ffffff | #cd0020 | #cd0020
71741 | Gubbio | #202952 | #ee2031 | #202952 | #202952
71742 | Guidonia Montecelio | #00316a | #d52020 | #00316a | #00316a
71743 | Latina Calcio 1932 | #2073b4 | #080808 | #2073b4 | #2073b4
71744 | Livorno 1915 | #732029 | #080808 | #732029 | #732029
71745 | Ostiamare Lido Calcio | #6218a4 | #ffffff | #6218a4 | #6218a4
71746 | Perugia | #e60000 | #ffffff | #e60000 | #e60000
71747 | Pianese | #182020 | #525a62 | #182020 | #182020
71748 | Pineto Calcio | #2073de | #ffffff | #2073de | #2073de
71749 | Ravenna | #941000 | #ffc531 | #941000 | #941000
71750 | Sambenedettese | #20204a | #cd1018 | #20204a | #20204a
71751 | Torres | #e60808 | #ffffff | #e60808 | #e60808
71752 | Vado | #00316a | #ee3139 | #00316a | #00316a
71753 | Vis Pesaro 1898 | #ffffff | #ee2031 | #ffffff | #ffffff
71754 | CD Atlas | #cd1829 | #080808 | #cd1829 | #cd1829
71755 | CD Guadalajara | #de0008 | #18314a | #de0008 | #de0008
71756 | CD Necaxa | #ffffff | #008331 | #ffffff | #ffffff
71757 | CD Santos Laguna | #ffffff | #20ac62 | #ffffff | #ffffff
71758 | CF Atlante | #002062 | #732029 | #002062 | #002062
71759 | CF Puebla de la Franja | #ffffff | #2073f6 | #ffffff | #ffffff
71760 | Club Atlético San Luis | #cd0020 | #00418b | #cd0020 | #cd0020
71761 | Club León | #006231 | #ffffff | #006231 | #006231
71762 | Deportivo Toluca | #e60000 | #080808 | #e60000 | #e60000
71763 | Fútbol Club Juárez | #8bee31 | #080808 | #8bee31 | #8bee31
71764 | Pachuca CF | #0031ac | #ffffff | #0031ac | #0031ac
71765 | Pumas de la UNAM | #ffffff | #08296a | #ffffff | #ffffff
71766 | Querétaro FC | #08528b | #080808 | #08528b | #08528b
71767 | Tijuana | #cd1829 | #080808 | #cd1829 | #cd1829
71768 | Almere City FC | #ee2020 | #080808 | #ee2020 | #ee2020
71769 | De Graafschap | #ffffff | #0052d5 | #ffffff | #ffffff
71770 | FC Den Bosch | #0052c5 | #ffffff | #0052c5 | #0052c5
71771 | FC Dordrecht | #ffffff | #10524a | #ffffff | #ffffff
71772 | FC Eindhoven | #ffffff | #0052d5 | #ffffff | #ffffff
71773 | FC Emmen | #de2929 | #ffffff | #de2929 | #de2929
71774 | Helmond Sport | #ee1010 | #080808 | #ee1010 | #ee1010
71775 | MVV Maastricht | #ffffff | #a40018 | #ffffff | #ffffff
71776 | RKC Waalwijk | #ffee29 | #3173bd | #ffee29 | #ffee29
71777 | Roda JC Kerkrade | #ffde00 | #080808 | #ffde00 | #ffde00
71778 | TOP Oss | #ffffff | #d51820 | #ffffff | #ffffff
71779 | Vitesse Arnhem | #080808 | #ffffff | #080808 | #080808
71780 | VVV-Venlo | #fff600 | #000000 | #fff600 | #fff600
71781 | Arbroath | #732029 | #ffffff | #732029 | #732029
71782 | Ayr United | #080808 | #ffffff | #080808 | #080808
71783 | Dunfermline Athletic | #ffffff | #080808 | #ffffff | #ffffff
71784 | Greenock Morton | #0062cd | #ffffff | #0062cd | #0062cd
71785 | Inverness CT | #3152a4 | #080808 | #3152a4 | #3152a4
71786 | Partick Thistle | #ffd500 | #080808 | #ffd500 | #ffd500
71787 | Queen's Park | #080808 | #ffffff | #080808 | #080808
71788 | Raith Rovers | #101831 | #ffffff | #101831 | #101831
71789 | Stenhousemuir | #620810 | #ffffff | #620810 | #620810
71790 | Alcorcón | #103183 | #deb429 | #103183 | #103183
71791 | Algeciras | #ffffff | #e60000 | #ffffff | #ffffff
71792 | Antequera C.F | #ffffff | #4ac57b | #ffffff | #ffffff
71793 | C.E. Europa | #ffffff | #0031a4 | #ffffff | #ffffff
71794 | Cartagena | #ffffff | #080808 | #ffffff | #ffffff
71795 | H. Alicante | #0052d5 | #ffffff | #0052d5 | #0052d5
71796 | Ibiza | #39bdff | #ffffff | #39bdff | #39bdff
71797 | Murcia | #ffffff | #cd1018 | #ffffff | #ffffff
71798 | R. Jaén | #ffffff | #52319c | #ffffff | #ffffff
71799 | R. Majadahonda | #ffffff | #002062 | #ffffff | #ffffff
71800 | Tarragona | #b40000 | #ffffff | #b40000 | #b40000
71801 | Teruel | #e60000 | #9c0000 | #e60000 | #e60000
71802 | Torremolinos | #ffffff | #008331 | #ffffff | #ffffff
71803 | U.E. Sant Andreu | #ffff39 | #080808 | #ffff39 | #ffff39
71805 | Águilas F.C | #ffffff | #6273ff | #ffffff | #ffffff
71806 | Etoile Carouge FC | #084a62 | #ffffff | #084a62 | #084a62
71807 | FC Aarau | #ffffff | #080808 | #ffffff | #ffffff
71808 | FC Rapperswil-Jona | #cd0020 | #ffffff | #cd0020 | #cd0020
71809 | FC Stade Lausanne-Ouchy | #bd0800 | #ffffff | #bd0800 | #bd0800
71810 | FC Stade Nyonnais | #ffd500 | #080808 | #ffd500 | #ffd500
71811 | FC Wil 1900 | #ffffff | #080808 | #ffffff | #ffffff
71812 | FC Winterthur | #ffffff | #d50018 | #ffffff | #ffffff
71813 | Neuchâtel Xamax FCS | #080808 | #de1820 | #080808 | #080808
71814 | SC Kriens | #ffffff | #006231 | #ffffff | #ffffff
71815 | Yverdon Sport FC | #004a39 | #ffffff | #004a39 | #004a39
71816 | Ankara Keçiörengücü | #ffffff | #410083 | #ffffff | #ffffff
71817 | Bandırma Spor | #f6f6f6 | #8b1820 | #f6f6f6 | #f6f6f6
71818 | Batman Petrol Spor A.Ş | #ffffff | #cd1018 | #ffffff | #ffffff
71819 | Bodrum Futbol Kulübü | #008331 | #004a29 | #008331 | #008331
71820 | Boluspor | #f6f6f6 | #ee1829 | #f6f6f6 | #f6f6f6
71821 | Bursaspor | #ffffff | #006231 | #ffffff | #ffffff
71822 | Esenler Erokspor | #204139 | #ffffff | #204139 | #204139
71823 | Iğdır Futbol Kulübü | #f6f6f6 | #008331 | #f6f6f6 | #f6f6f6
71824 | İstanbulspor A.Ş | #ffe610 | #080808 | #ffe610 | #ffe610
71825 | Manisa Futbol Kulübü | #ffffff | #f6f6f6 | #ffffff | #ffffff
71826 | Mardin 1969 Spor | #e60000 | #181039 | #e60000 | #e60000
71827 | Muğlaspor Kulübü | #ffffff | #007331 | #ffffff | #ffffff
71828 | Pendikspor Futbol A.Ş | #ffffff | #e60000 | #ffffff | #ffffff
71829 | Sarıyer | #f6f6f6 | #0839c5 | #f6f6f6 | #f6f6f6
71830 | Sivasspor | #f6f6f6 | #050808 | #f6f6f6 | #f6f6f6
71831 | Van Spor Futbol Kulübü | #d50000 | #080808 | #d50000 | #d50000
71832 | Ümraniyespor | #cd0020 | #f6f6f6 | #cd0020 | #cd0020
71833 | Birmingham Legion FC | #080808 | #9c8b5a | #080808 | #080808
71834 | Brooklyn FC | #080808 | #cdc5b4 | #080808 | #080808
71835 | Charleston Battery | #080808 | #ffcd08 | #080808 | #080808
71836 | Detroit City FC | #c59c29 | #411010 | #c59c29 | #c59c29
71837 | Hartford Athletic | #009c41 | #ffffff | #009c41 | #009c41
71838 | Indy Eleven | #102039 | #ffffff | #102039 | #102039
71839 | Loudoun United FC | #ee2029 | #ffffff | #ee2029 | #ee2029
71840 | Louisville City FC | #41007b | #080808 | #41007b | #41007b
71841 | Miami FC | #00319c | #eec562 | #00319c | #00319c
71842 | Pittsburgh Riverhounds | #ffe600 | #080808 | #ffe600 | #ffe600
71843 | Rhode Island FC | #001839 | #ffac00 | #001839 | #001839
71844 | Sporting JAX | #00acf6 | #ffa400 | #00acf6 | #00acf6
71845 | Tampa Bay Rowdies | #ffcd00 | #4a8b29 | #ffcd00 | #ffcd00
```

## NATIONAL TEAMS - do NOT output these
```
1 | Republic of Ireland
2 | Northern Ireland
3 | Scotland
4 | Wales
5 | England
6 | Portugal
7 | Spain
8 | France
9 | Belgium
10 | Netherlands
11 | Switzerland
12 | Italy
13 | Czech Republic
14 | Germany
15 | Denmark
16 | Norway
17 | Sweden
18 | Finland
19 | Poland
20 | Slovakia
21 | Austria
22 | Hungary
23 | Slovenia
24 | Croatia
26 | Romania
27 | Bulgaria
28 | Greece
29 | Turkey
30 | Ukraine
31 | Russia
32 | Morocco
33 | Tunisia
34 | Egypt
35 | Nigeria
36 | Cameroon
37 | South Africa
38 | Senegal
39 | USA
40 | Mexico
41 | Jamaica
42 | Costa Rica
43 | Honduras
44 | Colombia
45 | Brazil
46 | Peru
47 | Chile
48 | Paraguay
49 | Uruguay
50 | Argentina
51 | Ecuador
52 | Japan
53 | Korea Republic
54 | China
55 | Iran
56 | Saudi Arabia
57 | Australia
59 | Latvia
199 | PES United
1010 | Iraq
1011 | Jordan
1012 | Korea DPR
1013 | Kuwait
1015 | Lebanon
1022 | Oman
1026 | Qatar
1031 | Thailand
1032 | United Arab Emirates
1040 | Algeria
1041 | Angola
1044 | Burkina Faso
1046 | Cape Verde
1050 | DR Congo
1051 | Cote d Ivoire
1056 | Gabon
1058 | Ghana
1059 | Guinea
1067 | Mali
1083 | Zambia
1099 | Canada
1113 | Panama
1123 | Suriname
1124 | Curacao
1128 | Bolivia
1129 | Venezuela
1141 | New Zealand
1164 | Israel
1165 | Albania
1166 | Andorra
1167 | Armenia
1168 | Azerbaijan
1169 | Belarus
1170 | Bosnia and Herzegovina
1171 | Cyprus
1172 | Estonia
1173 | Faroe Islands
1174 | Georgia
1175 | Iceland
1176 | Kazakhstan
1177 | Liechtenstein
1178 | Lithuania
1179 | Luxembourg
1180 | North Macedonia
1181 | Malta
1182 | Moldova
1183 | San Marino
1184 | Uzbekistan
1550 | Serbia
1551 | Montenegro
2703 | European Classics
2704 | World Classics
5439 | Gibraltar
5440 | Kosovo
5749 | India
5750 | Indonesia
6002 | PES Legends Europe A
6003 | PES Legends Europe B
6004 | PES Legends World
6166 | Haiti
```

## SANITY CHECK BEFORE YOU ANSWER
- Row count equals the number of ids in Table A (743).
- Every id in Table A appears exactly once; no extra ids.
- Every colour matches `^#[0-9A-F]{6}$` and the three colours are not all identical.
- No national team from the list above leaked into the output.
