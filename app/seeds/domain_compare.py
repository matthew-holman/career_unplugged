from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.seeds.career_pages import SEED_LISTS


def normalize_host(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    # If it's already a bare domain, urlparse treats it as "path"
    if "://" not in value:
        host = value
    else:
        parsed = urlparse(value)
        host = parsed.netloc or parsed.path

    host = host.lower().rstrip("/")

    # Remove potential credentials and port
    host = host.split("@")[-1].split(":")[0]
    return host


def host_to_seed_dict(host: str) -> dict:
    """
    Convert a host like 'saltx.teamtailor.com' or 'foo.na.teamtailor.com'
    into the seed dict format:
      {
        "company_name": "<subdomain part>",
        "url": "https://<host>",
        "active": True,
      }
    company_name is derived from the left-most label (the subdomain).
    """
    host = normalize_host(host)
    if not host:
        raise ValueError("Empty host")

    # company_name = host.split("/", 1)[1]
    company_name = host.split(".", 1)[0]  # left-most label only
    return {
        "company_name": company_name,
        "url": f"https://{host}",
        "active": True,
    }


def diff_seed_dicts(
    seeds: list[dict],
    google_domains: Iterable[str],
) -> list[dict]:
    seed_hosts = {normalize_host(item["url"]) for item in seeds if item.get("url")}
    google_hosts = {normalize_host(d) for d in google_domains if normalize_host(d)}

    missing_hosts = sorted(google_hosts - seed_hosts)
    # intersection = google_hosts.intersection(seed_hosts)
    return [host_to_seed_dict(host) for host in missing_hosts]


google_domains_text = """\
adveez.teamtailor.com
aebr.teamtailor.com
again.teamtailor.com
alvalabs.teamtailor.com
arespartners.teamtailor.com
aulaenergy.na.teamtailor.com
autolivbrazil.teamtailor.com
autolivchina.teamtailor.com
autolivestonia.teamtailor.com
autolivfrance.teamtailor.com
autolivgroup.teamtailor.com
autolivheadoffice.teamtailor.com
autolivhungary.teamtailor.com
autolivindia.teamtailor.com
autolivspain.teamtailor.com
autolivsweden.teamtailor.com
autolivtaiwan.teamtailor.com
autolivthailand.teamtailor.com
autolivturkey.teamtailor.com
autolivunitedstates.teamtailor.com
blueair.teamtailor.com
bobw.teamtailor.com
brunswickrealestate.teamtailor.com
bryter.teamtailor.com
c3creativecodeandcontent.teamtailor.com
cappelendamm-amby.teamtailor.com
cdpglobal.teamtailor.com
celfocus.teamtailor.com
deepki.teamtailor.com
dfdspoland.teamtailor.com
dolead.teamtailor.com
ecobio.teamtailor.com
eitrawmaterialsgmbh.teamtailor.com
entail-amby.teamtailor.com
eoliann-1670252117.teamtailor.com
esadefaculty.teamtailor.com
eurobioimaging.teamtailor.com
fnality.teamtailor.com
fortrayglobalservices.teamtailor.com
friendsofeurope-1721722951.teamtailor.com
greenspherecapital-1743167981-source-certain.teamtailor.com
griegphilippines-1734015786.teamtailor.com
henryscheinone.teamtailor.com
holvi.teamtailor.com
huawei.teamtailor.com
huaweidenmark.teamtailor.com
huaweidusseldorf-1719303222.teamtailor.com
huaweifinland.teamtailor.com
huaweifinlandrnd.teamtailor.com
huaweiresearchcentergermanyaustria.teamtailor.com
huaweisweden.teamtailor.com
huaweitechnologiesitalia.teamtailor.com
huaweiuk.teamtailor.com
impetus.teamtailor.com
interruptlabs.teamtailor.com
italentplus.teamtailor.com
k3capitalgroup-1747925234-kbs-corporate.teamtailor.com
keyrusbelgium.teamtailor.com
keyrusmea.teamtailor.com
keyrusuk.teamtailor.com
knaufsemea.teamtailor.com
knaufsweden.teamtailor.com
lofavor-amby.teamtailor.com
lotuscars.teamtailor.com
lotuscarseurope.teamtailor.com
lotusuk.teamtailor.com
lotusukmanufacturing.teamtailor.com
macmillan.teamtailor.com
metizoft-amby.teamtailor.com
mintos.teamtailor.com
monese.teamtailor.com
montel.teamtailor.com
moonraillimited-1696577088.teamtailor.com
multiversecomputing.teamtailor.com
newseccom.teamtailor.com
noteless-amby.teamtailor.com
optiveumspzoo.teamtailor.com
panmacmillan.teamtailor.com
payex.teamtailor.com
pfx.teamtailor.com
prepaypower.teamtailor.com
pridelondon.teamtailor.com
ravenpack.teamtailor.com
rcseng.teamtailor.com
renoirconsulting.teamtailor.com
rootz.teamtailor.com
sallyqab.teamtailor.com
scoro-1669049295.teamtailor.com
senewsec.teamtailor.com
sicra-amby.teamtailor.com
silenteight.teamtailor.com
sipearl.teamtailor.com
sixsensesibiza.teamtailor.com
superawesome.teamtailor.com
support.teamtailor.com
swedbankpay.teamtailor.com
sybo.teamtailor.com
theworkshop.teamtailor.com
toppansecurity.teamtailor.com
tripletex-amby.teamtailor.com
upcloud.teamtailor.com
vento.teamtailor.com
vetmigo.teamtailor.com
vindai-amby.teamtailor.com
vividgamessa.teamtailor.com
yunoenergy.teamtailor.com
zapp-1672737080.teamtailor.com
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
