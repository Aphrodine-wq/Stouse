"""
Seed script for VibeHouse platform.

Populates the database with realistic demo data including users, vendors,
projects, phases, tasks, design artifacts, contracts, bids, daily reports,
and disputes.

Usage:
    python -m vibehouse.scripts.seed
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from vibehouse.common.enums import (
    BidStatus,
    ContractStatus,
    DesignArtifactType,
    DisputeStatus,
    DisputeType,
    PhaseType,
    ProjectStatus,
    TaskStatus,
    UserRole,
)
from vibehouse.common.security import get_password_hash
from vibehouse.db.models import (
    Bid,
    Contract,
    DailyReport,
    DesignArtifact,
    Dispute,
    Project,
    ProjectPhase,
    Task,
    User,
    Vendor,
)
from vibehouse.db.session import async_session_factory


async def main() -> None:
    async with async_session_factory() as session:
        # ------------------------------------------------------------------
        # Guard: skip if already seeded (check for admin user)
        # ------------------------------------------------------------------
        result = await session.execute(
            select(User).where(User.email == "admin@vibehouse.io")
        )
        if result.scalar_one_or_none() is not None:
            print("Database already seeded -- skipping.")
            return

        # ==================================================================
        # USERS
        # ==================================================================
        hashed = get_password_hash("testpass123")

        sarah = User(
            id=uuid.uuid4(),
            email="sarah@example.com",
            hashed_password=hashed,
            full_name="Sarah Chen",
            phone="(512) 555-0101",
            role=UserRole.HOMEOWNER,
            is_active=True,
            preferences={"notifications": True, "theme": "light"},
        )
        marcus = User(
            id=uuid.uuid4(),
            email="marcus@example.com",
            hashed_password=hashed,
            full_name="Marcus Johnson",
            phone="(512) 555-0102",
            role=UserRole.HOMEOWNER,
            is_active=True,
            preferences={"notifications": True, "theme": "dark"},
        )
        elena = User(
            id=uuid.uuid4(),
            email="elena@example.com",
            hashed_password=hashed,
            full_name="Elena Rodriguez",
            phone="(512) 555-0103",
            role=UserRole.CONTRACTOR,
            is_active=True,
            preferences={"notifications": True},
        )
        david = User(
            id=uuid.uuid4(),
            email="david@example.com",
            hashed_password=hashed,
            full_name="David Kim",
            phone="(512) 555-0104",
            role=UserRole.INSPECTOR,
            is_active=True,
            preferences={"notifications": True},
        )
        admin = User(
            id=uuid.uuid4(),
            email="admin@vibehouse.io",
            hashed_password=hashed,
            full_name="Admin User",
            phone="(512) 555-0100",
            role=UserRole.ADMIN,
            is_active=True,
            preferences={"notifications": True, "theme": "system"},
        )

        users = [sarah, marcus, elena, david, admin]
        session.add_all(users)

        # ==================================================================
        # VENDORS  (15 total, across multiple trades)
        # ==================================================================
        vendors_data = [
            # -- 3 General Contractors --
            {
                "company_name": "Summit Builders LLC",
                "contact_name": "James Hartwell",
                "email": "james@summitbuilders.com",
                "phone": "(512) 555-1001",
                "trades": ["general_contractor", "framing"],
                "license_info": {"number": "GC-2024-78123", "state": "TX", "expiry": "2027-06-30"},
                "insurance_info": {"provider": "Builders Mutual", "policy": "BM-889012", "coverage": "$2M"},
                "rating": 4.8,
                "total_projects": 47,
                "address": "2100 S Congress Ave, Austin, TX 78704",
                "location_lat": 30.2460,
                "location_lng": -97.7494,
                "service_radius_miles": 40,
                "is_verified": True,
                "bio": "Summit Builders has been delivering high-quality residential construction in Central Texas for over 15 years. We specialize in custom homes and major renovations with an emphasis on craftsmanship and client communication.",
            },
            {
                "company_name": "Pacific Construction Group",
                "contact_name": "Linda Tran",
                "email": "linda@pacificcg.com",
                "phone": "(512) 555-1002",
                "trades": ["general_contractor", "concrete"],
                "license_info": {"number": "GC-2023-45890", "state": "TX", "expiry": "2027-03-15"},
                "insurance_info": {"provider": "Hartford", "policy": "HF-223344", "coverage": "$3M"},
                "rating": 4.6,
                "total_projects": 32,
                "address": "8900 Research Blvd, Austin, TX 78758",
                "location_lat": 30.3710,
                "location_lng": -97.7260,
                "service_radius_miles": 50,
                "is_verified": True,
                "bio": "Pacific Construction Group brings West-Coast design sensibility to Texas construction. Our team focuses on modern, energy-efficient builds with sustainable materials and practices.",
            },
            {
                "company_name": "Heritage Homes Inc",
                "contact_name": "Robert Caldwell",
                "email": "robert@heritagehomes.com",
                "phone": "(512) 555-1003",
                "trades": ["general_contractor", "remodeling"],
                "license_info": {"number": "GC-2024-91204", "state": "TX", "expiry": "2027-09-30"},
                "insurance_info": {"provider": "Liberty Mutual", "policy": "LM-556677", "coverage": "$2.5M"},
                "rating": 4.5,
                "total_projects": 58,
                "address": "3401 Manchaca Rd, Austin, TX 78704",
                "location_lat": 30.2340,
                "location_lng": -97.7830,
                "service_radius_miles": 35,
                "is_verified": True,
                "bio": "Heritage Homes has been a trusted name in Austin home building since 2005. We take pride in blending timeless craftsmanship with modern building techniques.",
            },
            # -- 2 Electricians --
            {
                "company_name": "Lone Star Electric Co",
                "contact_name": "Miguel Santos",
                "email": "miguel@lonestarelectric.com",
                "phone": "(512) 555-2001",
                "trades": ["electrician", "solar"],
                "license_info": {"number": "EL-2024-33456", "state": "TX", "expiry": "2027-04-15"},
                "insurance_info": {"provider": "State Farm", "policy": "SF-778899", "coverage": "$1M"},
                "rating": 4.9,
                "total_projects": 112,
                "address": "5500 E Riverside Dr, Austin, TX 78741",
                "location_lat": 30.2310,
                "location_lng": -97.7190,
                "service_radius_miles": 45,
                "is_verified": True,
                "bio": "Licensed master electrician with 20 years of experience. We handle everything from residential wiring to smart home automation and solar panel installations.",
            },
            {
                "company_name": "Bright Spark Electrical",
                "contact_name": "Amanda Foster",
                "email": "amanda@brightspark.com",
                "phone": "(512) 555-2002",
                "trades": ["electrician"],
                "license_info": {"number": "EL-2023-67890", "state": "TX", "expiry": "2027-08-30"},
                "insurance_info": {"provider": "Allstate", "policy": "AS-334455", "coverage": "$1M"},
                "rating": 4.4,
                "total_projects": 65,
                "address": "1200 W 6th St, Austin, TX 78703",
                "location_lat": 30.2720,
                "location_lng": -97.7580,
                "service_radius_miles": 30,
                "is_verified": True,
                "bio": "Bright Spark Electrical provides reliable, code-compliant electrical services for new construction and renovation projects throughout the Austin metro area.",
            },
            # -- 2 Plumbers --
            {
                "company_name": "AquaFlow Plumbing",
                "contact_name": "Derek Williams",
                "email": "derek@aquaflowplumbing.com",
                "phone": "(512) 555-3001",
                "trades": ["plumber", "gas_fitting"],
                "license_info": {"number": "PL-2024-11234", "state": "TX", "expiry": "2027-05-31"},
                "insurance_info": {"provider": "Travelers", "policy": "TR-990011", "coverage": "$1.5M"},
                "rating": 4.7,
                "total_projects": 89,
                "address": "7800 Burnet Rd, Austin, TX 78757",
                "location_lat": 30.3540,
                "location_lng": -97.7380,
                "service_radius_miles": 40,
                "is_verified": True,
                "bio": "AquaFlow Plumbing has served Austin homeowners and builders for over a decade. We specialize in new construction plumbing, re-piping, and tankless water heater installations.",
            },
            {
                "company_name": "Central Texas Piping Solutions",
                "contact_name": "Karen O'Brien",
                "email": "karen@ctpiping.com",
                "phone": "(512) 555-3002",
                "trades": ["plumber"],
                "license_info": {"number": "PL-2023-55678", "state": "TX", "expiry": "2027-02-28"},
                "insurance_info": {"provider": "Nationwide", "policy": "NW-112233", "coverage": "$1M"},
                "rating": 4.3,
                "total_projects": 44,
                "address": "4400 N Lamar Blvd, Austin, TX 78756",
                "location_lat": 30.3120,
                "location_lng": -97.7420,
                "service_radius_miles": 35,
                "is_verified": False,
                "bio": "Reliable plumbing solutions for residential construction. We pride ourselves on clean work, honest pricing, and timely project completion.",
            },
            # -- 2 Roofers --
            {
                "company_name": "Texas Top Roofing",
                "contact_name": "Carlos Mendez",
                "email": "carlos@texastoproofing.com",
                "phone": "(512) 555-4001",
                "trades": ["roofer", "gutters"],
                "license_info": {"number": "RF-2024-22345", "state": "TX", "expiry": "2027-07-31"},
                "insurance_info": {"provider": "USAA", "policy": "US-445566", "coverage": "$2M"},
                "rating": 4.6,
                "total_projects": 73,
                "address": "9200 N IH-35, Austin, TX 78753",
                "location_lat": 30.3780,
                "location_lng": -97.6870,
                "service_radius_miles": 50,
                "is_verified": True,
                "bio": "Texas Top Roofing is your go-to for residential roofing in the greater Austin area. We install asphalt shingles, metal roofing, and tile with manufacturer-certified crews.",
            },
            {
                "company_name": "Capital City Roofing",
                "contact_name": "Whitney Harper",
                "email": "whitney@capitalcityroofing.com",
                "phone": "(512) 555-4002",
                "trades": ["roofer"],
                "license_info": {"number": "RF-2023-88901", "state": "TX", "expiry": "2027-01-31"},
                "insurance_info": {"provider": "Progressive", "policy": "PG-667788", "coverage": "$1.5M"},
                "rating": 4.2,
                "total_projects": 38,
                "address": "2800 E Cesar Chavez St, Austin, TX 78702",
                "location_lat": 30.2520,
                "location_lng": -97.7200,
                "service_radius_miles": 30,
                "is_verified": True,
                "bio": "Capital City Roofing specializes in modern roofing systems. Standing seam metal, architectural shingles, and flat roof solutions for contemporary home designs.",
            },
            # -- 2 HVAC Companies --
            {
                "company_name": "CoolBreeze HVAC Services",
                "contact_name": "Tony Nguyen",
                "email": "tony@coolbreezehvac.com",
                "phone": "(512) 555-5001",
                "trades": ["hvac", "ductwork"],
                "license_info": {"number": "HV-2024-44567", "state": "TX", "expiry": "2027-06-30"},
                "insurance_info": {"provider": "Zurich", "policy": "ZR-889900", "coverage": "$1M"},
                "rating": 4.7,
                "total_projects": 95,
                "address": "6300 Cameron Rd, Austin, TX 78723",
                "location_lat": 30.3260,
                "location_lng": -97.6940,
                "service_radius_miles": 45,
                "is_verified": True,
                "bio": "CoolBreeze HVAC keeps Austin homes comfortable year-round. We design and install high-efficiency heating and cooling systems, including ductless mini-splits and smart thermostats.",
            },
            {
                "company_name": "Hill Country Climate Control",
                "contact_name": "Brenda Marshall",
                "email": "brenda@hcclimate.com",
                "phone": "(512) 555-5002",
                "trades": ["hvac"],
                "license_info": {"number": "HV-2023-99012", "state": "TX", "expiry": "2027-10-31"},
                "insurance_info": {"provider": "Chubb", "policy": "CH-112244", "coverage": "$1.5M"},
                "rating": 4.5,
                "total_projects": 52,
                "address": "11400 Bee Cave Rd, Austin, TX 78738",
                "location_lat": 30.2920,
                "location_lng": -97.8460,
                "service_radius_miles": 40,
                "is_verified": True,
                "bio": "Serving the Hill Country and greater Austin. We specialize in energy-efficient HVAC solutions designed for the Texas climate, including geothermal systems.",
            },
            # -- 2 Landscapers --
            {
                "company_name": "Austin Native Landscapes",
                "contact_name": "Rachel Green",
                "email": "rachel@austinnativelandscapes.com",
                "phone": "(512) 555-6001",
                "trades": ["landscaper", "irrigation"],
                "license_info": {"number": "LS-2024-66789", "state": "TX", "expiry": "2027-04-30"},
                "insurance_info": {"provider": "Farmers", "policy": "FM-334466", "coverage": "$500K"},
                "rating": 4.8,
                "total_projects": 130,
                "address": "5100 E Ben White Blvd, Austin, TX 78741",
                "location_lat": 30.2200,
                "location_lng": -97.7310,
                "service_radius_miles": 35,
                "is_verified": True,
                "bio": "We design and install beautiful, drought-resistant landscapes using native Texas plants. Our xeriscaping and rainwater harvesting systems help you conserve water while enjoying a stunning outdoor space.",
            },
            {
                "company_name": "Green Horizon Outdoor Living",
                "contact_name": "Patrick Sullivan",
                "email": "patrick@greenhorizon.com",
                "phone": "(512) 555-6002",
                "trades": ["landscaper", "hardscape"],
                "license_info": {"number": "LS-2023-33456", "state": "TX", "expiry": "2027-12-31"},
                "insurance_info": {"provider": "Erie", "policy": "ER-556688", "coverage": "$750K"},
                "rating": 3.9,
                "total_projects": 28,
                "address": "14000 N MoPac Expy, Austin, TX 78728",
                "location_lat": 30.4350,
                "location_lng": -97.7060,
                "service_radius_miles": 50,
                "is_verified": False,
                "bio": "Green Horizon creates outdoor living spaces that extend your home into nature. Patios, pergolas, outdoor kitchens, and full landscape design and installation.",
            },
            # -- 2 Interior Finishers --
            {
                "company_name": "Refined Interiors Co",
                "contact_name": "Sophia Patel",
                "email": "sophia@refinedinteriors.com",
                "phone": "(512) 555-7001",
                "trades": ["interior_finish", "painting", "drywall"],
                "license_info": {"number": "IF-2024-77890", "state": "TX", "expiry": "2027-05-15"},
                "insurance_info": {"provider": "Berkshire", "policy": "BH-778800", "coverage": "$1M"},
                "rating": 4.9,
                "total_projects": 84,
                "address": "1800 E 4th St, Austin, TX 78702",
                "location_lat": 30.2570,
                "location_lng": -97.7280,
                "service_radius_miles": 30,
                "is_verified": True,
                "bio": "Refined Interiors delivers flawless finishes for discerning homeowners. From custom cabinetry and trim to designer paint and wallcoverings, we bring your interior vision to life.",
            },
            {
                "company_name": "Austin Finish Works",
                "contact_name": "Nathan Brooks",
                "email": "nathan@austinfinishworks.com",
                "phone": "(512) 555-7002",
                "trades": ["interior_finish", "flooring", "tile"],
                "license_info": {"number": "IF-2023-44567", "state": "TX", "expiry": "2027-08-15"},
                "insurance_info": {"provider": "Geico Commercial", "policy": "GC-990022", "coverage": "$750K"},
                "rating": 3.5,
                "total_projects": 19,
                "address": "3600 S Lamar Blvd, Austin, TX 78704",
                "location_lat": 30.2380,
                "location_lng": -97.7920,
                "service_radius_miles": 25,
                "is_verified": False,
                "bio": "Specializing in flooring, tile, and finish carpentry for new construction and remodel projects. Hardwood, luxury vinyl, porcelain, and natural stone installations.",
            },
        ]

        vendor_objects: list[Vendor] = []
        for vd in vendors_data:
            v = Vendor(id=uuid.uuid4(), **vd)
            vendor_objects.append(v)
        session.add_all(vendor_objects)

        # Convenient references for later use
        summit = vendor_objects[0]       # Summit Builders LLC (GC)
        pacific = vendor_objects[1]      # Pacific Construction Group (GC)
        heritage = vendor_objects[2]     # Heritage Homes Inc (GC)
        lone_star_electric = vendor_objects[3]   # Lone Star Electric Co
        bright_spark = vendor_objects[4]         # Bright Spark Electrical
        aquaflow = vendor_objects[5]     # AquaFlow Plumbing
        texas_top_roof = vendor_objects[7]       # Texas Top Roofing
        coolbreeze = vendor_objects[9]   # CoolBreeze HVAC Services
        austin_native = vendor_objects[11]       # Austin Native Landscapes
        refined_interiors = vendor_objects[13]   # Refined Interiors Co

        # ==================================================================
        # PROJECTS
        # ==================================================================
        today = date(2026, 2, 28)
        project_start = today - timedelta(days=95)

        # --- Project 1: Modern Farmhouse on Riverside (Sarah) ---
        proj1 = Project(
            id=uuid.uuid4(),
            owner_id=sarah.id,
            title="Modern Farmhouse on Riverside",
            status=ProjectStatus.IN_PROGRESS,
            vibe_description=(
                "A modern farmhouse aesthetic blending rustic warmth with clean contemporary "
                "lines. Open floor plan, shiplap accent walls, black steel-framed windows, "
                "wide-plank white oak floors, and a chef's kitchen with a 12-foot island. "
                "Covered back porch overlooking a landscaped yard with mature oaks."
            ),
            address="4521 Riverside Dr, Austin, TX 78741",
            location_lat=30.2420,
            location_lng=-97.7250,
            budget=Decimal("450000.00"),
            budget_spent=Decimal("187500.00"),
            trello_board_id="trello_board_abc123",
        )

        # --- Project 2: Craftsman Cottage (Sarah) ---
        proj2 = Project(
            id=uuid.uuid4(),
            owner_id=sarah.id,
            title="Craftsman Cottage",
            status=ProjectStatus.DESIGNING,
            vibe_description=(
                "A charming Craftsman-style cottage with tapered columns, exposed rafter tails, "
                "and a welcoming front porch. Interior features built-in bookshelves, a stone "
                "fireplace, and warm wood tones throughout. Two bedrooms, one and a half baths, "
                "detached garage with a studio above."
            ),
            address="789 Bouldin Ave, Austin, TX 78704",
            location_lat=30.2450,
            location_lng=-97.7580,
            budget=Decimal("280000.00"),
            budget_spent=Decimal("0.00"),
        )

        # --- Project 3: Lake Travis Dream Home (Sarah) ---
        proj3 = Project(
            id=uuid.uuid4(),
            owner_id=sarah.id,
            title="Lake Travis Dream Home",
            status=ProjectStatus.DRAFT,
            vibe_description=(
                "A sprawling lakefront estate with floor-to-ceiling windows capturing panoramic "
                "views of Lake Travis. Hill Country stone exterior, infinity pool with spa, "
                "outdoor kitchen, wine cellar, home theater, and a private dock. Five bedrooms, "
                "six and a half bathrooms across three levels."
            ),
            address="1200 Lakeshore Dr, Lakeway, TX 78734",
            location_lat=30.3580,
            location_lng=-97.9780,
            budget=Decimal("750000.00"),
            budget_spent=Decimal("0.00"),
        )

        # --- Project 4: Urban Modern Loft Conversion (Marcus) ---
        proj4 = Project(
            id=uuid.uuid4(),
            owner_id=marcus.id,
            title="Urban Modern Loft Conversion",
            status=ProjectStatus.PLANNING,
            vibe_description=(
                "Converting a historic downtown warehouse into a sleek modern loft. Exposed "
                "brick walls, polished concrete floors, steel beams, floor-to-ceiling industrial "
                "windows. Open concept living with a floating mezzanine bedroom, chef's kitchen, "
                "and rooftop deck."
            ),
            address="310 E 3rd St, Austin, TX 78701",
            location_lat=30.2640,
            location_lng=-97.7390,
            budget=Decimal("180000.00"),
            budget_spent=Decimal("0.00"),
        )

        session.add_all([proj1, proj2, proj3, proj4])

        # ==================================================================
        # PHASES for Project 1  (all 9 PhaseType)
        # ==================================================================
        phase_configs = [
            # (PhaseType, status, start_date, end_date, budget_allocated, budget_spent, order)
            (PhaseType.SITE_PREP, TaskStatus.COMPLETED, project_start, project_start + timedelta(days=14), Decimal("25000.00"), Decimal("24200.00"), 0),
            (PhaseType.FOUNDATION, TaskStatus.COMPLETED, project_start + timedelta(days=15), project_start + timedelta(days=35), Decimal("55000.00"), Decimal("53800.00"), 1),
            (PhaseType.FRAMING, TaskStatus.COMPLETED, project_start + timedelta(days=36), project_start + timedelta(days=60), Decimal("65000.00"), Decimal("63500.00"), 2),
            (PhaseType.ROOFING, TaskStatus.IN_PROGRESS, project_start + timedelta(days=61), None, Decimal("40000.00"), Decimal("18000.00"), 3),
            (PhaseType.MEP, TaskStatus.BACKLOG, None, None, Decimal("70000.00"), Decimal("0.00"), 4),
            (PhaseType.INTERIOR, TaskStatus.BACKLOG, None, None, Decimal("85000.00"), Decimal("0.00"), 5),
            (PhaseType.EXTERIOR, TaskStatus.BACKLOG, None, None, Decimal("45000.00"), Decimal("0.00"), 6),
            (PhaseType.LANDSCAPE, TaskStatus.BACKLOG, None, None, Decimal("35000.00"), Decimal("0.00"), 7),
            (PhaseType.FINAL, TaskStatus.BACKLOG, None, None, Decimal("30000.00"), Decimal("0.00"), 8),
        ]

        phases: dict[PhaseType, ProjectPhase] = {}
        for pt, status, sd, ed, ba, bs, oi in phase_configs:
            phase = ProjectPhase(
                id=uuid.uuid4(),
                project_id=proj1.id,
                phase_type=pt,
                status=status,
                start_date=sd,
                end_date=ed,
                budget_allocated=ba,
                budget_spent=bs,
                order_index=oi,
            )
            phases[pt] = phase
        session.add_all(phases.values())

        # ==================================================================
        # TASKS for Project 1  (44 tasks across all phases)
        # ==================================================================
        task_count = 0

        def make_task(
            phase_type: PhaseType,
            title: str,
            status: TaskStatus,
            order: int,
            due_date_val: date | None = None,
            description: str | None = None,
            assignee_id: uuid.UUID | None = None,
        ) -> Task:
            nonlocal task_count
            task_count += 1
            return Task(
                id=uuid.uuid4(),
                phase_id=phases[phase_type].id,
                title=title,
                description=description,
                status=status,
                assignee_id=assignee_id,
                due_date=due_date_val,
                order_index=order,
            )

        # helper dates
        sp_start = project_start
        fn_start = project_start + timedelta(days=15)
        fr_start = project_start + timedelta(days=36)
        rf_start = project_start + timedelta(days=61)

        tasks: list[Task] = []

        # --- SITE_PREP (4 tasks, all completed) ---
        tasks.append(make_task(PhaseType.SITE_PREP, "Survey and stake property boundaries", TaskStatus.COMPLETED, 0, sp_start + timedelta(days=2), "Professional survey of lot lines and setback requirements", summit.id))
        tasks.append(make_task(PhaseType.SITE_PREP, "Clear vegetation and grade site", TaskStatus.COMPLETED, 1, sp_start + timedelta(days=6), "Remove trees as marked, clear brush, rough grade for drainage"))
        tasks.append(make_task(PhaseType.SITE_PREP, "Install erosion control and silt fencing", TaskStatus.COMPLETED, 2, sp_start + timedelta(days=8), "Install silt fence along property perimeter per SWPPP plan"))
        tasks.append(make_task(PhaseType.SITE_PREP, "Set up temporary utilities and construction entrance", TaskStatus.COMPLETED, 3, sp_start + timedelta(days=12), "Temp power pole, water meter, portable facilities, rock entrance"))

        # --- FOUNDATION (5 tasks, all completed) ---
        tasks.append(make_task(PhaseType.FOUNDATION, "Excavate for foundation footings", TaskStatus.COMPLETED, 0, fn_start + timedelta(days=4), "Excavate to 24-inch depth per structural plan", summit.id))
        tasks.append(make_task(PhaseType.FOUNDATION, "Install foundation forms and rebar", TaskStatus.COMPLETED, 1, fn_start + timedelta(days=8), "Set forms, place #5 rebar at 12-inch on center both ways"))
        tasks.append(make_task(PhaseType.FOUNDATION, "Pour concrete foundation walls", TaskStatus.COMPLETED, 2, fn_start + timedelta(days=12), "4000 PSI concrete, 4-inch slump, vibrate and finish"))
        tasks.append(make_task(PhaseType.FOUNDATION, "Waterproof and damp-proof foundation", TaskStatus.COMPLETED, 3, fn_start + timedelta(days=16), "Apply liquid membrane waterproofing and install drain tile"))
        tasks.append(make_task(PhaseType.FOUNDATION, "Backfill and compact around foundation", TaskStatus.COMPLETED, 4, fn_start + timedelta(days=19), "Backfill in 8-inch lifts, compact to 95% Proctor density"))

        # --- FRAMING (6 tasks, all completed) ---
        tasks.append(make_task(PhaseType.FRAMING, "Install sill plates and first floor deck", TaskStatus.COMPLETED, 0, fr_start + timedelta(days=3), "Anchor bolts, sill seal, pressure-treated sill plates, floor joists and subfloor", summit.id))
        tasks.append(make_task(PhaseType.FRAMING, "Frame exterior walls and raise", TaskStatus.COMPLETED, 1, fr_start + timedelta(days=7), "2x6 exterior walls with OSB sheathing, Tyvek house wrap"))
        tasks.append(make_task(PhaseType.FRAMING, "Frame interior partition walls", TaskStatus.COMPLETED, 2, fr_start + timedelta(days=10), "2x4 interior partitions per floor plan, blocking for cabinets"))
        tasks.append(make_task(PhaseType.FRAMING, "Install second floor joists and subfloor", TaskStatus.COMPLETED, 3, fr_start + timedelta(days=14), "Engineered I-joists at 16-inch OC, 3/4-inch AdvanTech subfloor"))
        tasks.append(make_task(PhaseType.FRAMING, "Frame second floor walls and gable ends", TaskStatus.COMPLETED, 4, fr_start + timedelta(days=18), "Complete second floor wall framing and gable end framing"))
        tasks.append(make_task(PhaseType.FRAMING, "Install windows and exterior doors (rough openings)", TaskStatus.COMPLETED, 5, fr_start + timedelta(days=22), "Set windows with flashing tape, install exterior door frames"))

        # --- ROOFING (4 tasks: 2 completed, 1 in_progress, 1 scheduled) ---
        tasks.append(make_task(PhaseType.ROOFING, "Install roof trusses", TaskStatus.COMPLETED, 0, rf_start + timedelta(days=5), "Crane-set engineered trusses at 24-inch OC per truss plan", texas_top_roof.id))
        tasks.append(make_task(PhaseType.ROOFING, "Sheath roof deck and install underlayment", TaskStatus.COMPLETED, 1, rf_start + timedelta(days=10), "7/16 OSB roof sheathing, synthetic underlayment, ice and water shield at valleys and eaves", texas_top_roof.id))
        tasks.append(make_task(PhaseType.ROOFING, "Install standing seam metal roofing", TaskStatus.IN_PROGRESS, 2, rf_start + timedelta(days=20), "24-gauge Galvalume standing seam panels, ridge cap, valley flashing", texas_top_roof.id))
        tasks.append(make_task(PhaseType.ROOFING, "Install gutters and downspouts", TaskStatus.SCHEDULED, 3, rf_start + timedelta(days=25), "6-inch seamless aluminum gutters, 3x4 downspouts, splash blocks"))

        # --- MEP (4 tasks, all backlog) ---
        tasks.append(make_task(PhaseType.MEP, "Rough-in electrical wiring and panel", TaskStatus.BACKLOG, 0, description="200-amp service panel, run circuits per electrical plan, low-voltage wiring for data and security", assignee_id=lone_star_electric.id))
        tasks.append(make_task(PhaseType.MEP, "Rough-in plumbing supply and DWV", TaskStatus.BACKLOG, 1, description="PEX supply lines, ABS drain/waste/vent, water heater connections", assignee_id=aquaflow.id))
        tasks.append(make_task(PhaseType.MEP, "Install HVAC ductwork and equipment", TaskStatus.BACKLOG, 2, description="Two-zone HVAC system, flex duct runs, register boots, condensate drain", assignee_id=coolbreeze.id))
        tasks.append(make_task(PhaseType.MEP, "MEP rough-in inspection", TaskStatus.BACKLOG, 3, description="Schedule and pass city inspection for all mechanical, electrical, and plumbing rough-in"))

        # --- INTERIOR (8 tasks, all backlog) ---
        tasks.append(make_task(PhaseType.INTERIOR, "Install batt and spray foam insulation", TaskStatus.BACKLOG, 0, description="R-19 batt in walls, R-38 blown in attic, closed-cell spray foam at rim joists"))
        tasks.append(make_task(PhaseType.INTERIOR, "Hang and finish drywall", TaskStatus.BACKLOG, 1, description="1/2-inch drywall throughout, 5/8-inch moisture-resistant in baths, Level 4 finish", assignee_id=refined_interiors.id))
        tasks.append(make_task(PhaseType.INTERIOR, "Install interior trim and millwork", TaskStatus.BACKLOG, 2, description="Shaker-style door casings, 7-inch baseboards, crown molding in living areas", assignee_id=refined_interiors.id))
        tasks.append(make_task(PhaseType.INTERIOR, "Prime and paint all interior surfaces", TaskStatus.BACKLOG, 3, description="Two coats Sherwin-Williams Emerald, accent walls per design plan", assignee_id=refined_interiors.id))
        tasks.append(make_task(PhaseType.INTERIOR, "Install kitchen cabinets and countertops", TaskStatus.BACKLOG, 4, description="Custom shaker cabinets, quartz countertops with waterfall edge on island"))
        tasks.append(make_task(PhaseType.INTERIOR, "Install hardwood and tile flooring", TaskStatus.BACKLOG, 5, description="White oak hardwood in living areas, porcelain tile in baths and laundry"))
        tasks.append(make_task(PhaseType.INTERIOR, "Install plumbing fixtures and trim", TaskStatus.BACKLOG, 6, description="Kohler fixtures throughout, farmhouse sink, rain shower heads", assignee_id=aquaflow.id))
        tasks.append(make_task(PhaseType.INTERIOR, "Install electrical fixtures, switches, and outlets", TaskStatus.BACKLOG, 7, description="Recessed LED lighting, pendant fixtures, Decora switches and outlets", assignee_id=lone_star_electric.id))

        # --- EXTERIOR (4 tasks, all backlog) ---
        tasks.append(make_task(PhaseType.EXTERIOR, "Install exterior siding and stone veneer", TaskStatus.BACKLOG, 0, description="Board and batten fiber cement siding, natural stone veneer on lower facade"))
        tasks.append(make_task(PhaseType.EXTERIOR, "Build covered back porch and deck", TaskStatus.BACKLOG, 1, description="24x14 covered porch with cedar tongue-and-groove ceiling, composite decking"))
        tasks.append(make_task(PhaseType.EXTERIOR, "Install garage door and exterior hardware", TaskStatus.BACKLOG, 2, description="Insulated carriage-style garage door with smart opener"))
        tasks.append(make_task(PhaseType.EXTERIOR, "Apply exterior paint and stain", TaskStatus.BACKLOG, 3, description="Exterior paint in Agreeable Gray, black window trim, stain porch ceiling"))

        # --- LANDSCAPE (4 tasks, all backlog) ---
        tasks.append(make_task(PhaseType.LANDSCAPE, "Install irrigation system", TaskStatus.BACKLOG, 0, description="Smart drip and spray irrigation zones, rain sensor, Wi-Fi controller", assignee_id=austin_native.id))
        tasks.append(make_task(PhaseType.LANDSCAPE, "Grade and prepare planting beds", TaskStatus.BACKLOG, 1, description="Final grade, amend soil with compost, install landscape fabric and edging", assignee_id=austin_native.id))
        tasks.append(make_task(PhaseType.LANDSCAPE, "Plant trees, shrubs, and perennials", TaskStatus.BACKLOG, 2, description="Native TX plants: live oaks, Mexican plum, salvia, muhly grass, yaupon holly", assignee_id=austin_native.id))
        tasks.append(make_task(PhaseType.LANDSCAPE, "Install sod, mulch, and landscape lighting", TaskStatus.BACKLOG, 3, description="Bermuda sod in lawn areas, 3-inch cedar mulch in beds, low-voltage path lighting", assignee_id=austin_native.id))

        # --- FINAL (5 tasks, all backlog) ---
        tasks.append(make_task(PhaseType.FINAL, "Final clean and punch list walkthrough", TaskStatus.BACKLOG, 0, description="Deep clean entire house, create punch list of deficiencies with homeowner"))
        tasks.append(make_task(PhaseType.FINAL, "Complete punch list items", TaskStatus.BACKLOG, 1, description="Address all items identified during walkthrough"))
        tasks.append(make_task(PhaseType.FINAL, "Final building inspection and certificate of occupancy", TaskStatus.BACKLOG, 2, description="Schedule final inspection with city, obtain CO"))
        tasks.append(make_task(PhaseType.FINAL, "Install appliances and final fixtures", TaskStatus.BACKLOG, 3, description="Kitchen appliance suite, washer/dryer, garage door opener programming"))
        tasks.append(make_task(PhaseType.FINAL, "Homeowner orientation and warranty handoff", TaskStatus.BACKLOG, 4, description="Walk homeowner through all systems, provide manuals, warranty documents, and maintenance schedule"))

        session.add_all(tasks)

        # ==================================================================
        # DESIGN ARTIFACTS
        # ==================================================================
        # --- Project 1: 3 design artifacts (floor plans) ---
        da1 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj1.id,
            artifact_type=DesignArtifactType.FLOOR_PLAN,
            version=1,
            title="Modern Farmhouse - Option A (Open Concept)",
            description="Primary floor plan with fully open great room, kitchen, and dining. Master suite on first floor with en-suite bath and walk-in closet.",
            file_url="/artifacts/proj1/floor_plan_option_a_v1.pdf",
            metadata_={"rooms": 4, "bathrooms": 3.5, "sqft": 2800, "stories": 2, "source": "vibe_engine"},
            is_selected=True,
        )
        da2 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj1.id,
            artifact_type=DesignArtifactType.FLOOR_PLAN,
            version=1,
            title="Modern Farmhouse - Option B (Dual Living)",
            description="Split floor plan with dual living areas. Formal dining room separated from casual breakfast nook. Master on second floor.",
            file_url="/artifacts/proj1/floor_plan_option_b_v1.pdf",
            metadata_={"rooms": 4, "bathrooms": 3, "sqft": 2650, "stories": 2, "source": "vibe_engine"},
            is_selected=False,
        )
        da3 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj1.id,
            artifact_type=DesignArtifactType.ELEVATION,
            version=1,
            title="Modern Farmhouse - Front Elevation",
            description="Front elevation rendering showing board-and-batten siding, black steel windows, covered entry porch, and standing seam metal roof.",
            file_url="/artifacts/proj1/front_elevation_v1.pdf",
            metadata_={"style": "modern_farmhouse", "source": "vibe_engine"},
            is_selected=True,
        )

        # --- Project 2: 3 floor plan design artifacts ---
        da4 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj2.id,
            artifact_type=DesignArtifactType.FLOOR_PLAN,
            version=1,
            title="Craftsman Cottage - Plan A (Classic Layout)",
            description="Traditional Craftsman layout with central hallway, living room with built-ins, and cozy kitchen. Detached garage with studio.",
            file_url="/artifacts/proj2/floor_plan_a_v1.pdf",
            metadata_={"rooms": 2, "bathrooms": 1.5, "sqft": 1400, "stories": 1, "source": "vibe_engine"},
            is_selected=False,
        )
        da5 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj2.id,
            artifact_type=DesignArtifactType.FLOOR_PLAN,
            version=1,
            title="Craftsman Cottage - Plan B (Open Kitchen)",
            description="Updated layout with open kitchen flowing into living room. Larger master bath with soaking tub. Covered side porch.",
            file_url="/artifacts/proj2/floor_plan_b_v1.pdf",
            metadata_={"rooms": 2, "bathrooms": 1.5, "sqft": 1500, "stories": 1, "source": "vibe_engine"},
            is_selected=False,
        )
        da6 = DesignArtifact(
            id=uuid.uuid4(),
            project_id=proj2.id,
            artifact_type=DesignArtifactType.FLOOR_PLAN,
            version=1,
            title="Craftsman Cottage - Plan C (Loft Addition)",
            description="Adds a loft space above the living room for a reading nook or home office. Vaulted ceilings with exposed beams.",
            file_url="/artifacts/proj2/floor_plan_c_v1.pdf",
            metadata_={"rooms": 2, "bathrooms": 1.5, "sqft": 1650, "stories": 1.5, "source": "vibe_engine"},
            is_selected=False,
        )

        session.add_all([da1, da2, da3, da4, da5, da6])

        # ==================================================================
        # CONTRACTS  (2 for project 1)
        # ==================================================================
        contract1 = Contract(
            id=uuid.uuid4(),
            project_id=proj1.id,
            vendor_id=summit.id,
            scope="General construction services for Modern Farmhouse on Riverside including site preparation, foundation, framing, exterior finishes, and project management.",
            amount=Decimal("320000.00"),
            status=ContractStatus.ACTIVE,
            start_date=project_start,
            end_date=project_start + timedelta(days=210),
            milestones=[
                {"name": "Foundation complete", "amount": "55000.00", "due_date": str(project_start + timedelta(days=35)), "status": "paid"},
                {"name": "Framing complete", "amount": "65000.00", "due_date": str(project_start + timedelta(days=60)), "status": "paid"},
                {"name": "Dry-in complete", "amount": "40000.00", "due_date": str(project_start + timedelta(days=85)), "status": "pending"},
                {"name": "Interior rough-in complete", "amount": "70000.00", "due_date": str(project_start + timedelta(days=130)), "status": "pending"},
                {"name": "Substantial completion", "amount": "90000.00", "due_date": str(project_start + timedelta(days=200)), "status": "pending"},
            ],
            terms={
                "payment_terms": "Net 15 upon milestone completion",
                "warranty": "1 year workmanship warranty",
                "change_order_process": "Written approval required for any scope changes",
                "insurance_required": True,
            },
        )

        contract2 = Contract(
            id=uuid.uuid4(),
            project_id=proj1.id,
            vendor_id=lone_star_electric.id,
            scope="Complete electrical installation for residential new construction including service entrance, panel, branch circuits, lighting, and low-voltage wiring.",
            amount=Decimal("45000.00"),
            status=ContractStatus.ACTIVE,
            start_date=project_start + timedelta(days=61),
            end_date=project_start + timedelta(days=170),
            milestones=[
                {"name": "Rough-in complete", "amount": "25000.00", "due_date": str(project_start + timedelta(days=100)), "status": "pending"},
                {"name": "Trim-out and finals", "amount": "20000.00", "due_date": str(project_start + timedelta(days=165)), "status": "pending"},
            ],
            terms={
                "payment_terms": "Net 15 upon milestone completion",
                "warranty": "2 year workmanship, manufacturer warranty on fixtures",
                "insurance_required": True,
            },
        )

        session.add_all([contract1, contract2])

        # ==================================================================
        # BIDS  (3 bids for project 1)
        # ==================================================================
        bid1 = Bid(
            id=uuid.uuid4(),
            vendor_id=summit.id,
            project_id=proj1.id,
            amount=Decimal("320000.00"),
            scope_description="Full general contracting services including site prep, foundation, framing, roofing oversight, and exterior finishes. Excludes MEP subcontractors.",
            timeline_days=210,
            status=BidStatus.ACCEPTED.value,
            details={"includes_permits": True, "includes_dumpster": True, "crew_size": 8},
        )
        bid2 = Bid(
            id=uuid.uuid4(),
            vendor_id=pacific.id,
            project_id=proj1.id,
            amount=Decimal("345000.00"),
            scope_description="Turnkey general contracting with all trades included. Premium materials and energy-efficient building envelope.",
            timeline_days=240,
            status=BidStatus.REJECTED.value,
            details={"includes_permits": True, "includes_dumpster": True, "crew_size": 6},
        )
        bid3 = Bid(
            id=uuid.uuid4(),
            vendor_id=heritage.id,
            project_id=proj1.id,
            amount=Decimal("298000.00"),
            scope_description="General contracting services for structure and shell only. Homeowner to contract MEP and finishes separately.",
            timeline_days=195,
            status=BidStatus.REJECTED.value,
            details={"includes_permits": False, "includes_dumpster": True, "crew_size": 5},
        )

        session.add_all([bid1, bid2, bid3])

        # ==================================================================
        # DAILY REPORTS  (5 reports for project 1, Feb 24-28 2026)
        # ==================================================================
        report_base_date = date(2026, 2, 24)

        report_contents = [
            # Day 1 - Feb 24
            {
                "date": "2026-02-24",
                "project_title": "Modern Farmhouse on Riverside",
                "executive_summary": "Project is 45% complete. Roof truss delivery completed on schedule. Electrical rough-in preparation has begun in the master suite wing. Weather conditions were favorable with clear skies and temperatures in the mid-60s.",
                "task_progress": {"total_tasks": 42, "completed": 19, "in_progress": 5, "blocked": 1, "completion_percent": 45.2},
                "budget_summary": {"total_budget": "450000.00", "total_spent": "187500.00", "remaining": "262500.00", "burn_rate_percent": 41.7, "alert_level": "green"},
                "schedule_health": {"days_elapsed": 91, "estimated_total_days": 210, "percent_complete": 45.2, "days_ahead_behind": 2, "status": "on_track"},
                "activities_today": [
                    "Roof truss delivery and staging in staging area",
                    "Crane mobilization for truss setting tomorrow",
                    "Electrical rough-in started in master suite",
                    "Framing inspection sign-off received from city",
                ],
                "risk_alerts": [
                    {"severity": "medium", "category": "weather", "message": "Rain expected Thursday - may delay roofing installation"},
                    {"severity": "low", "category": "supply_chain", "message": "Standing seam metal panels on backorder - ETA March 1"},
                ],
                "upcoming_milestones": [
                    "Roof truss installation (Feb 25-26)",
                    "Roof sheathing and underlayment (Feb 27-28)",
                    "Metal roofing installation (est. March 3-8)",
                ],
            },
            # Day 2 - Feb 25
            {
                "date": "2026-02-25",
                "project_title": "Modern Farmhouse on Riverside",
                "executive_summary": "Strong progress today with roof trusses set on the main structure. Crane operation went smoothly with all trusses placed and braced by 3 PM. Electrician continued rough-in in master bath area.",
                "task_progress": {"total_tasks": 42, "completed": 19, "in_progress": 5, "blocked": 1, "completion_percent": 46.1},
                "budget_summary": {"total_budget": "450000.00", "total_spent": "189200.00", "remaining": "260800.00", "burn_rate_percent": 42.0, "alert_level": "green"},
                "schedule_health": {"days_elapsed": 92, "estimated_total_days": 210, "percent_complete": 46.1, "days_ahead_behind": 2, "status": "on_track"},
                "activities_today": [
                    "All 28 roof trusses set and temporarily braced",
                    "Crane demobilized by end of day",
                    "Electrical rough-in continued - master bath circuits pulled",
                    "Plumbing subcontractor site visit for MEP planning",
                ],
                "risk_alerts": [
                    {"severity": "medium", "category": "weather", "message": "Rain still expected Thursday - tarps staged for roof protection"},
                ],
                "upcoming_milestones": [
                    "Roof sheathing start (Feb 26)",
                    "Roofing completion (est. March 5)",
                    "MEP rough-in inspection (est. March 12)",
                ],
            },
            # Day 3 - Feb 26
            {
                "date": "2026-02-26",
                "project_title": "Modern Farmhouse on Riverside",
                "executive_summary": "Roof sheathing is underway with 60% of the deck completed. Permanent truss bracing installed. A minor issue with one truss requiring shimming was resolved on-site by the framing crew.",
                "task_progress": {"total_tasks": 42, "completed": 20, "in_progress": 5, "blocked": 0, "completion_percent": 47.6},
                "budget_summary": {"total_budget": "450000.00", "total_spent": "191000.00", "remaining": "259000.00", "burn_rate_percent": 42.4, "alert_level": "green"},
                "schedule_health": {"days_elapsed": 93, "estimated_total_days": 210, "percent_complete": 47.6, "days_ahead_behind": 3, "status": "ahead"},
                "activities_today": [
                    "Roof sheathing - 60% complete (main roof and garage wing)",
                    "Permanent truss bracing and hurricane clips installed",
                    "One truss bearing point shimmed to correct 1/4-inch sag",
                    "Received standing seam panel color samples for owner review",
                ],
                "risk_alerts": [
                    {"severity": "low", "category": "weather", "message": "Thursday rain downgraded to scattered showers - should not impact work significantly"},
                ],
                "upcoming_milestones": [
                    "Complete roof sheathing (Feb 27)",
                    "Underlayment and ice/water shield (Feb 28)",
                    "Metal roofing installation (est. March 3-8)",
                ],
            },
            # Day 4 - Feb 27
            {
                "date": "2026-02-27",
                "project_title": "Modern Farmhouse on Riverside",
                "executive_summary": "Roof sheathing completed ahead of schedule. Underlayment installation has started on the south-facing slopes. Homeowner visited site and approved the Charcoal Grey standing seam color selection.",
                "task_progress": {"total_tasks": 42, "completed": 21, "in_progress": 4, "blocked": 0, "completion_percent": 50.0},
                "budget_summary": {"total_budget": "450000.00", "total_spent": "193500.00", "remaining": "256500.00", "burn_rate_percent": 43.0, "alert_level": "green"},
                "schedule_health": {"days_elapsed": 94, "estimated_total_days": 210, "percent_complete": 50.0, "days_ahead_behind": 4, "status": "ahead"},
                "activities_today": [
                    "Roof sheathing 100% complete - passed nail pattern inspection",
                    "Synthetic underlayment started on south slopes",
                    "Ice and water shield installed at all valleys and eave lines",
                    "Homeowner approved Charcoal Grey standing seam color",
                    "Confirmed metal panel delivery date: March 1",
                ],
                "risk_alerts": [],
                "upcoming_milestones": [
                    "Complete underlayment (Feb 28)",
                    "Metal panel delivery (March 1)",
                    "Standing seam installation begins (March 3)",
                ],
            },
            # Day 5 - Feb 28
            {
                "date": "2026-02-28",
                "project_title": "Modern Farmhouse on Riverside",
                "executive_summary": "Project hits 50% milestone! Underlayment installation is complete. Building is now weathertight with temporary protection. Light scattered showers this afternoon did not impact work. Ready for metal roofing installation next week.",
                "task_progress": {"total_tasks": 42, "completed": 21, "in_progress": 3, "blocked": 0, "completion_percent": 51.2},
                "budget_summary": {"total_budget": "450000.00", "total_spent": "195000.00", "remaining": "255000.00", "burn_rate_percent": 43.3, "alert_level": "green"},
                "schedule_health": {"days_elapsed": 95, "estimated_total_days": 210, "percent_complete": 51.2, "days_ahead_behind": 4, "status": "ahead"},
                "activities_today": [
                    "Underlayment installation 100% complete",
                    "All roof penetration boots and pipe flashings installed",
                    "Drip edge installed at all eaves and rakes",
                    "Light rain in afternoon - no impact due to completed underlayment",
                    "HVAC subcontractor submitted ductwork shop drawings for review",
                ],
                "risk_alerts": [
                    {"severity": "low", "category": "coordination", "message": "HVAC ductwork drawings need architect review before MEP rough-in can begin"},
                ],
                "upcoming_milestones": [
                    "Metal panel delivery (March 1)",
                    "Standing seam roofing installation (March 3-8)",
                    "Gutter and downspout installation (March 9-10)",
                    "MEP rough-in begins (est. March 11)",
                ],
            },
        ]

        reports: list[DailyReport] = []
        for i, content in enumerate(report_contents):
            rpt_date = report_base_date + timedelta(days=i)
            reports.append(
                DailyReport(
                    id=uuid.uuid4(),
                    project_id=proj1.id,
                    report_date=rpt_date,
                    content=content,
                    summary=content["executive_summary"],
                    sent_at=datetime(rpt_date.year, rpt_date.month, rpt_date.day, 18, 0, 0, tzinfo=timezone.utc),
                )
            )
        session.add_all(reports)

        # ==================================================================
        # DISPUTE  (1 active dispute on project 1)
        # ==================================================================
        dispute = Dispute(
            id=uuid.uuid4(),
            project_id=proj1.id,
            filed_by_id=sarah.id,
            status=DisputeStatus.DIRECT_RESOLUTION,
            dispute_type=DisputeType.QUALITY,
            title="Framing alignment issue in master bedroom wall",
            description=(
                "During a site visit on Feb 20, I noticed the master bedroom north wall "
                "appears to bow inward approximately 3/4 inch over an 8-foot span. This "
                "exceeds the acceptable tolerance per our contract specifications. The "
                "framing crew states it is within normal range, but my independent "
                "measurement confirms the deviation. Requesting correction before drywall."
            ),
            parties=[
                {"role": "homeowner", "name": "Sarah Chen", "user_id": str(sarah.id)},
                {"role": "contractor", "name": "Summit Builders LLC", "vendor_id": str(summit.id)},
            ],
            resolution=None,
            resolution_options=[
                {"option": "Sister additional stud to straighten wall", "proposed_by": "contractor", "estimated_cost": "350.00"},
                {"option": "Remove and reframe entire wall section", "proposed_by": "homeowner", "estimated_cost": "2800.00"},
                {"option": "Install furring strips to create flat drywall plane", "proposed_by": "mediator", "estimated_cost": "600.00"},
            ],
            resolution_deadline=datetime(2026, 3, 7, 23, 59, 59, tzinfo=timezone.utc),
            escalated_at=None,
            resolved_at=None,
            history=[
                {"date": "2026-02-20T14:30:00Z", "action": "filed", "by": "Sarah Chen", "note": "Dispute filed after site visit"},
                {"date": "2026-02-21T09:15:00Z", "action": "status_change", "from": "identified", "to": "direct_resolution", "note": "Parties agreed to attempt direct resolution"},
                {"date": "2026-02-22T11:00:00Z", "action": "options_proposed", "note": "Three resolution options documented"},
            ],
        )
        session.add(dispute)

        # ==================================================================
        # COMMIT
        # ==================================================================
        await session.commit()

        # ==================================================================
        # SUMMARY
        # ==================================================================
        print(
            f"Seeded: {len(users)} users, {len(vendor_objects)} vendors, "
            f"4 projects, {task_count} tasks, {len(reports)} reports"
        )


if __name__ == "__main__":
    asyncio.run(main())
