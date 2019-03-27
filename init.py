# -*- coding: utf-8 -*-
import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from ffpasta import models



price_categories = [{
    'name': 'těstoviny',
    'unit_price': 100,
}, {
    'name': 'pesta',
    'unit_price': 100,
}]

pastas = [{
    'name': 'casareccia',
    'length': 0,
    'img': 'casareccia.png',
    'description': 'Esíčka jsou širší zarolované kousky těstoviny s výrazným stočením na konci. Jedná se o nejoblíbenější druh těstovin u našich zákazníků, jsou skvělé jak do omáček, salátů nebo jako příloha.',
}, {
    'name': 'conchiglie',
    'length': 0,
    'img': 'conchiglie.png',
    'description': 'Mušle jsou ideální těstovinou na saláty, nebo k masovému ragu. Conchiglie překvapí svou variabilitou. Skvěle se hodí i na zapékané pokrmy.'
}, {
    'name': 'fusilli',
    'length': 0,
    'img': 'fusilli.png',
    'description': 'Vřeténka nebo vrtule jsou vhodné do zeleninových salátů, jednoduše s bylinkovým pestem nebo k masovým omáčkám. Díky svému tvaru udrží těstovina velké množství omáčky.',
}, {
    'name': 'penne',
    'length': 0,
    'img': 'penne.png',
    'description': 'Penne jsou krátké vroubkované a zkosené trubičky. Jemně vroubkovaný povrch těstoviny skvěle drží omáčku. Těstovina je nejvhodnější ke smetanovým a sýrovým omáčkám.',
}, {
    'name': 'lasagne',
    'length': 1,
    'img': 'lasagne.png',
    'description': 'Lasagne jsou velmi široké, lisované těstoviny ve tvaru obdélníků, které se vždy pečou. Nejtradičnější recepty jsou Lasagne Bolognese, kdy se střídají vrstvy těstovinových plátů, bešamelu a masa (neapolské ragů).',
}, {
    'name': 'linguine',
    'length': 1,
    'img': 'linguine.png',
    'description': 'Linguine jsou těstoviny podobné spaghettám, pouze tenčí a placaté. Jde o velmi jemnou těstovinu nejčastěji používanou s pestem nebo mořskými plody.',
}, {
    'name': 'pappardelle',
    'length': 1,
    'img': 'pappardelle.png',
    'description': 'Pappardellle jsou 2-3 cm široké ploché těstoviny, velice oblíbené pro svou schopnost držet omáčku.',
}, {
    'name': 'spaghetti',
    'length': 1,
    'img': 'spaghetti.png',
    'description': 'Spaghetti jsou nejrozšířenějším typem těstovin a zároveň italským národním jídlem. Jedná se o tenkou válcovitou těstovinu nejčastěji podávanou s rajčatovými omáčkami, bylinkami, posypané parmazánem.',
}, {
    'name': 'tagliatelle',
    'length': 1,
    'img': 'tagliatelle.png',
    'description': 'Tagliatelle jsou dlouhé ploché široké nudle, šířka těchto těstovin je 0,65 - 1 cm. Těstovina je nejčastěji podávaná s různými druhy ragů.',
}]

reasons = [{
    'header': 'Rychlá příprava',
    'ffpasta': '3 min.',
    'others': '8-12 min.',
    'img': 'time.png',
}, {
    'header': 'Víte co jíte',
    'ffpasta': 'Bez barviv a konzervatů z kvalitní italské mouky a českých vajec',
    'others': 'Původ i složení často neznámé',
    'img': 'know.png',
}, {
    'header': 'Vhodné při redukční dietě',
    'ffpasta': 'Nízký glykemický index, vyšší nutriční hodnoty, zasytí na delší dobu',
    'others': 'Vyšší glykemický index, nízké nutriční hodnoty',
    'img': 'diet.png',
}, {
    'header': 'Chuť',
    'ffpasta': 'Výraznější, sytější, díky čerstvosti lépe natáhne omáčku. Těstoviny jsou syrové, rychle zachlazené',
    'others': 'Nevýrazná, pro zasycení je nutná větší porce',
    'img': 'taste.png',
}, {
    'header': 'Čerstvost',
    'ffpasta': 'Těstoviny jsou syrové, rychle zachlazené',
    'others': 'Často přesušené, 12 – 24 měsíců staré, v lepším případě předvařené nebo mražené',
    'img': 'fresh.png',
}]

sections = [{
    'headline': 'druhy těstovin',
    'link': 'těstoviny',
    'text': None,
    'widget': 'i',
}, {
    'headline': 'proč naše těstoviny',
    'link': 'proč my',
    'text': '<p>FF Pasta jsou čerstv&eacute;, rychle připraviteln&eacute; těstoviny skl&aacute;daj&iacute;c&iacute; se ze dvou druhů italsk&eacute; p&scaron;eničn&eacute; mouky a česk&yacute;ch vaj&iacute;ček (Semolina / Farina / česk&aacute; vaj&iacute;čka v poměru: 2 / 1 / 0,7).</p>'
              '<p>Těstoviny jsou lehce straviteln&eacute;, maj&iacute; n&iacute;zk&yacute; obsah tuku, jsou bohat&eacute; na uhlovod&iacute;ky. Pro lidsk&yacute; organismus jsou těstoviny d&iacute;ky obsahu glycidů v&yacute;znamn&yacute;m zdrojem energie. Obsahuj&iacute; značn&eacute; množstv&iacute; proteinů, kter&eacute; maj&iacute; svůj v&yacute;znam i při redukci hmotnosti.</p>',
    'widget': 'r',
}, {
    'headline': 'dodáváme',
    'link': 'dodáváme',
    'text': '<p>Těstoviny dod&aacute;v&aacute;me nav&aacute;žen&eacute; v uzav&iacute;rateln&yacute;ch potravinov&yacute;ch boxech po 3 &ndash; 7 kg (dle druhu těstoviny a skladovac&iacute;ch kapacit klienta). Uveden&eacute; plastov&eacute; boxy pln&iacute; hygienick&eacute; normy pro skladov&aacute;n&iacute; a je možně v nich skladovat těstoviny v lednici vedle ostatn&iacute;ch potravin (u zeleniny i masa).</p>'
            '<p>Rozvoz 2x t&yacute;dně chlad&iacute;c&iacute;m vozem. Minim&aacute;ln&iacute; objednan&eacute; množstv&iacute; je 10 kg. Osobn&iacute; odběr v provozovně - Křeme&scaron;nick&aacute; 824, Pelhřimov, druh&eacute; patro nad prodejnou Mountfield.</p>'
            '<p>Objedn&aacute;vky, objedn&aacute;vkov&yacute; formul&aacute;ř &ndash; www.ffpasta.cz/objednavky, emailem &ndash; objednavky@ffpasta.cz, telefonicky - +420 720 309 514</p>'
            '<h2 style="text-align:center">Speci&aacute;lně pro &scaron;koln&iacute; j&iacute;delny a z&aacute;vodn&iacute; stravov&aacute;n&iacute;</h2>'
            '<p>Na&scaron;im c&iacute;lem je přispět ke zkvalitněn&iacute; stravov&aacute;n&iacute; ve &scaron;koln&iacute;ch a z&aacute;vodn&iacute;ch j&iacute;deln&aacute;ch. Čerstvou surovinu je nutn&eacute; i kvalitně připravit. S prvn&iacute; dod&aacute;vku těstovin do va&scaron;&iacute; j&iacute;delny přijede kuchař, kter&yacute; pro&scaron;kol&iacute; person&aacute;l v př&iacute;pravě a skladov&aacute;n&iacute; čerstv&yacute;ch těstovin, doporuč&iacute; vhodn&eacute; recepty.</p>'
            '<p>V na&scaron;em t&yacute;mu nechyb&iacute; ani odbornice na v&yacute;živu, kter&aacute; v&aacute;m pomůže s kalkulac&iacute; j&iacute;del a spotřebn&iacute;m ko&scaron;em.</p>',
    'widget': None,
}, {
    'headline': 'o nás',
    'link': 'o nás',
    'text': '<p>Jsme jedin&yacute;m v&yacute;robce čerstv&yacute;ch těstovin na Vysočině. K produkci využ&iacute;v&aacute;me nejnověj&scaron;&iacute; italsk&eacute; stroje.</p>'
            '<p>V na&scaron;em t&yacute;mu je zku&scaron;en&yacute; kuchař s prax&iacute; z italsk&yacute;ch restaurac&iacute; a odbornice na v&yacute;živov&eacute; poradenstv&iacute; a v&yacute;chovu ke zdrav&iacute;. Můžeme tak věcně radit a pom&aacute;hat v&scaron;em odběratelům s př&iacute;pravou menu a receptů s ohledem na jejich cenu a v&yacute;živov&eacute; hodnoty.</p>'
            '<p>Stali jsme se soci&aacute;ln&iacute;m podnikem zaměstn&aacute;vaj&iacute;c&iacute;m děti opou&scaron;těj&iacute;c&iacute; dětsk&eacute; domovy a zdravotně znev&yacute;hodněn&eacute;.</p>',
    'widget': None,
}, {
    'headline': 'kontakt',
    'link': 'kontakt',
    'text': '<p>Filip Hložek<br />'
            'Vnitřn&iacute; 973<br />'
            '393 01 Pelhřimov<br />'
            'IČ 04706412<br />'
            '+420 720 309 514<br />'
            'info@FFpasta.cz</p>',
    'widget': 'c',
}]


if not models.PriceCategory.objects.all().exists():
    for p in price_categories:
        print(p['name'])
        models.PriceCategory(name=p['name'], unit_price=p['unit_price']).save()

if not models.Pasta.objects.all().exists():
    price_category = models.PriceCategory.objects.first()
    for p in pastas:
        print(p['name'])
        models.Pasta(name=p['name'], description=p['description'], img=p['img'], length=p['length'], price_category=price_category,
                       published=True, active=True).save()

if not models.Difference.objects.all().exists():
    for r in reasons:
        print(r['header'])
        models.Difference(header=r['header'], ffpasta=r['ffpasta'], others=r['others'], img=r['img'], published=True).save()

if not models.Section.objects.all().exists():
    for s in sections:
        print(s['headline'])
        models.Section(headline=s['headline'], link=s['link'], text=s['text'], widget=s['widget']).save()
