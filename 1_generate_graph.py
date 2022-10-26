import pandas as pd
import json
import matplotlib.pyplot as plt
from datetime import datetime

taker = "takerVolumeBuy"
institution = "institutionVolumeBuy"
nonInstitution = "nonInstitutionVolumeBuy"


def get_data_dict() -> dict:
    return json.load(open("exchange_stats.json", "r"))['data']


def generate_dataframe_from_dict(input_dict) -> pd.DataFrame:
    for entry in input_dict:
        entry['datetime'] = datetime.fromtimestamp(entry['timestamp'])
        entry['takerBuyRatio'] = entry[taker] / entry[taker.replace("Buy", "Sell")]
        entry['institutionBuyRatio'] = entry[institution] / entry[institution.replace("Buy", "Sell")]
        entry['nonInstitutionBuyRatio'] = entry[nonInstitution] / entry[nonInstitution.replace("Buy", "Sell")]
    dframe = pd.DataFrame(input_dict)
    dframe.set_index('timestamp', inplace=True)
    return dframe


df = generate_dataframe_from_dict(get_data_dict())
ax = df.plot(x="datetime", y="takerBuyRatio", kind="line", color="tab:cyan")
df.plot(x="datetime", y="institutionBuyRatio", kind="line", ax=ax, color="tab:green")
df.plot(x="datetime", y="nonInstitutionBuyRatio", kind="line", ax=ax, color="tab:gray")
plt.axhline(y=1, color="k", linestyle='-')

ax2 = ax.twinx()
df.plot(x="datetime", y="price", kind="line", ax=ax2, color="tab:orange")

plt.legend()
plt.show()
