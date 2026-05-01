from __future__ import annotations

from datetime import date, datetime

import pandas as pd

DateLike = str | date | datetime | pd.Timestamp
