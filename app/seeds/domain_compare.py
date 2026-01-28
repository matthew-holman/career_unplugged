from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.seeds.career_pages import SEED_LISTS


def key_to_seed_dict(key: str) -> dict:
    """
    key is canonical host+path, e.g.:
      - "panmacmillan.teamtailor.com"
      - "job-boards.eu.greenhouse.io/wunderflats"
    """
    key = key.strip().lstrip("/")
    if not key:
        raise ValueError("Empty url key")

    if "/" in key:
        host, path = key.split("/", 1)
        company_name = path.split("/")[-1]  # last segment
        url = f"https://{host}/{path}"
    else:
        host = key
        company_name = host.split(".", 1)[0]  # left-most label
        url = f"https://{host}"

    return {
        "company_name": company_name,
        "url": url,
        "active": True,
    }


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    # Ensure urlparse puts the host in netloc
    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)

    host = (parsed.netloc or "").lower()

    # Remove potential credentials and port
    host = host.split("@")[-1].split(":")[0]

    path = (parsed.path or "").rstrip("/")

    # Canonical form: host + path (no scheme, no query, no fragment)
    return f"{host}{path}"


def diff_seed_dicts(
    seeds: list[dict],
    google_domains: Iterable[str],
) -> list[dict]:
    seed_keys = {normalize_url(item["url"]) for item in seeds if item.get("url")}
    google_keys = {normalize_url(d) for d in google_domains if normalize_url(d)}

    missing_hosts = sorted(google_keys - seed_keys)
    # intersection = google_keys.intersection(seed_keys)
    return [key_to_seed_dict(host) for host in missing_hosts]


google_domains_text = """\
feebris.careers.hibob.com
kiteworks.careers.hibob.com
stellarentertainment.careers.hibob.com
theasiagroup.careers.hibob.com
communauto.careers.hibob.com
intelligentlending.careers.hibob.com
powermart.careers.hibob.com
theinsightsfamily.careers.hibob.com
modernsynthesis.careers.hibob.com
rvscareers.careers.hibob.com
corlytics.careers.hibob.com
dbag.careers.hibob.com
docupace.careers.hibob.com
pairpoint.careers.hibob.com
stileeducation.careers.hibob.com
tixly.careers.hibob.com
credrails.careers.hibob.com
optimussearch.careers.hibob.com
semarchy.careers.hibob.com
tws.careers.hibob.com
wbcsd.careers.hibob.com
apploi.careers.hibob.com
envevo.careers.hibob.com
thewildernesssociety.careers.hibob.com
proveai.careers.hibob.com
bamboocard.careers.hibob.com
vechain.careers.hibob.com
verder-3d58e643f0324.careers.hibob.com
wemeanbusinessco.careers.hibob.com
2heads.careers.hibob.com
50sport.careers.hibob.com
8b.careers.hibob.com
additionallengths.careers.hibob.com
advance-he.careers.hibob.com
alliants.careers.hibob.com
allocatr.careers.hibob.com
analogueinsight.careers.hibob.com
aofrio.careers.hibob.com
appliedcomput-e669c6.careers.hibob.com
aspectcapital-94a5ce.careers.hibob.com
astropay.careers.hibob.com
atptourinc.careers.hibob.com
audionetwork.careers.hibob.com
autorek.careers.hibob.com
bamboocard.careers.hibob.com
basemc.careers.hibob.com
bernsteinshur.careers.hibob.com
bioinnovation-3d109d.careers.hibob.com
bjarkeingelsgroup.careers.hibob.com
blanccotechno-d3e7bd.careers.hibob.com
bondbrandloyalty.careers.hibob.com
bwwater-makingwaves.careers.hibob.com
careers.hibob.com
carringtonwest.careers.hibob.com
chillys.careers.hibob.com
citizensadvic-d6feef.careers.hibob.com
cleanfoundation.careers.hibob.com
compassmsp.careers.hibob.com
conet.careers.hibob.com
corlytics.careers.hibob.com
creaturecomforts.careers.hibob.com
credrails.careers.hibob.com
cri.careers.hibob.com
crimtan.careers.hibob.com
depowise.careers.hibob.com
dfl-group.careers.hibob.com
dockbay.careers.hibob.com
docupace.careers.hibob.com
dswiss.careers.hibob.com
dufrainconsulting.careers.hibob.com
ecarstrade.careers.hibob.com
ecologi.careers.hibob.com
egetis.careers.hibob.com
elementalenergies.careers.hibob.com
enclustragmbh.careers.hibob.com
energix-group.careers.hibob.com
energyone.careers.hibob.com
entrepreneursfirst.careers.hibob.com
equiteq.careers.hibob.com
eurowaggroup.careers.hibob.com
evenergy.careers.hibob.com
everythingfinancial.careers.hibob.com
fairheatltd.careers.hibob.com
farratisolevelltd.careers.hibob.com
feefo.careers.hibob.com
fime.careers.hibob.com
firemind.careers.hibob.com
fleetspace.careers.hibob.com
food4education1.careers.hibob.com
freemanseventcareers.careers.hibob.com
fuellearning.careers.hibob.com
fulhamfc.careers.hibob.com
geminor.careers.hibob.com
generalindex.careers.hibob.com
genesiscancercareuk.careers.hibob.com
genoox.careers.hibob.com
getgotechnologies.careers.hibob.com
globalfashionagenda.careers.hibob.com
globalmaritime.careers.hibob.com
goredistrictcouncil.careers.hibob.com
gresham.careers.hibob.com
group-ib-acd1038c3ae.careers.hibob.com
growupfarms.careers.hibob.com
hectare.careers.hibob.com
hibob-e360.careers.hibob.com
hlms.careers.hibob.com
honeycoin.careers.hibob.com
hooposystemsltd.careers.hibob.com
hubbox.careers.hibob.com
identity.careers.hibob.com
idh.careers.hibob.com
impaxassetmanagement.careers.hibob.com
infinigate.careers.hibob.com
info.careers.hibob.com
ito.careers.hibob.com
itoworld.careers.hibob.com
joinus.careers.hibob.com
kamma.careers.hibob.com
kaptio.careers.hibob.com
keyengineering.careers.hibob.com
kiddiecapersc-4697a4.careers.hibob.com
kiteworks.careers.hibob.com
leaflivingopcoltd.careers.hibob.com
leboncoin.careers.hibob.com
legentic.careers.hibob.com
librasoftwaregroup.careers.hibob.com
liquidia.careers.hibob.com
localpayment.careers.hibob.com
lochardenergy.careers.hibob.com
londonmarathongr.careers.hibob.com
lovewellblake.careers.hibob.com
luca.careers.hibob.com
manuportlogistics.careers.hibob.com
markit.careers.hibob.com
meandu.careers.hibob.com
mediaforce.careers.hibob.com
meridiangroup-2da458.careers.hibob.com
mightyape.careers.hibob.com
millertanner.careers.hibob.com
mlltelecomltd.careers.hibob.com
moment.careers.hibob.com
monumentbanklimited.careers.hibob.com
mycroschoolinc.careers.hibob.com
obts.careers.hibob.com
odysseytherapeut.careers.hibob.com
onegroupsolutions.careers.hibob.com
oosto.careers.hibob.com
optimised.careers.hibob.com
orbis.careers.hibob.com
otrium.careers.hibob.com
pairpoint.careers.hibob.com
pencil.careers.hibob.com
phoenix2retail.careers.hibob.com
piabgroup.careers.hibob.com
planetinnovation.careers.hibob.com
planetsport.careers.hibob.com
playable-marketing.careers.hibob.com
plusxinnovation.careers.hibob.com
polarperforma-21253f.careers.hibob.com
powermart.careers.hibob.com
proactis.careers.hibob.com
proveai.careers.hibob.com
providertrust.careers.hibob.com
pulsarexposro.careers.hibob.com
pure.careers.hibob.com
qxi.careers.hibob.com
reachuniversity.careers.hibob.com
realtimeagency.careers.hibob.com
redwoodbank.careers.hibob.com
rms.careers.hibob.com
rosterfy.careers.hibob.com
scorebuddy.careers.hibob.com
secretescapes.careers.hibob.com
semarchy.careers.hibob.com
sensopro.careers.hibob.com
serpentinegallery.careers.hibob.com
settlemint.careers.hibob.com
shulmanpartnersllp.careers.hibob.com
sourceintelligence.careers.hibob.com
spectarium.careers.hibob.com
springstudios.careers.hibob.com
stellarentertainment.careers.hibob.com
stori.careers.hibob.com
sumdog.careers.hibob.com
sunzinet.careers.hibob.com
sustaincert.careers.hibob.com
synpulse.careers.hibob.com
techniche.careers.hibob.com
thearenagroup.careers.hibob.com
thebiodiversi-b3c692.careers.hibob.com
thecollective.careers.hibob.com
theedlongcorpora.careers.hibob.com
theinsightsfamily.careers.hibob.com
themathergroup.careers.hibob.com
theselfspace.careers.hibob.com
thesis.careers.hibob.com
thinkforthefuture.careers.hibob.com
tis.careers.hibob.com
tispayments.careers.hibob.com
titancloudsof-37f14a.careers.hibob.com
torq-partners.careers.hibob.com
torqpartners-people.careers.hibob.com
tracsis.careers.hibob.com
transmission.careers.hibob.com
transmissioni-7e8bf9.careers.hibob.com
trustpayments.careers.hibob.com
uncommon.careers.hibob.com
unidays.careers.hibob.com
urbint.careers.hibob.com
valr.careers.hibob.com
vector8.careers.hibob.com
velocys.careers.hibob.com
verder-3d58e643f0324.careers.hibob.com
vicemedia.careers.hibob.com
viewber.careers.hibob.com
vivedia.careers.hibob.com
wagworks.careers.hibob.com
wayoflife.careers.hibob.com
wbcsd.careers.hibob.com
wemeanbusinessco.careers.hibob.com
wiredscore.careers.hibob.com
wisestamp.careers.hibob.com
wizard.careers.hibob.com
zenzero.careers.hibob.com
zepz.careers.hibob.com
"""


def main():

    google_domains = [line for line in google_domains_text.splitlines() if line.strip()]
    master_list = [page for page_list in SEED_LISTS for page in page_list]
    missing_seed_dicts: list[dict] = diff_seed_dicts(master_list, google_domains)

    print(f"Missing ({len(missing_seed_dicts)}):")
    for item in missing_seed_dicts:
        print(str(item) + ",")


if __name__ == "__main__":
    main()
