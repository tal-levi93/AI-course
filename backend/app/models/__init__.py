# Models are registered here so Base.metadata sees them.
from app.models.user import User  # noqa: F401
from app.models.household import Household, Membership  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
