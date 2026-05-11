DDMRP Inventory Planning System — Execution PRD + SSOT Blueprint
Based on the uploaded HTML prototype and Excel workbook, this document defines the exact implementation blueprint for building the production-ready demo application using:


Backend → Flask


Database → Supabase (PostgreSQL)


Frontend → HTML/CSS/Vanilla JS


Uploads → CSV/XLSX bulk upload


Real-time updates → polling/WebSocket-lite


UI → must match uploaded HTML structure exactly 



1. Product Goal
Build a minimal but fully functional DDMRP inventory planning application where:


Users upload daily stock CSV/XLSX files.


Data is validated.


Inventory planning calculations run automatically.


Buffer zones and recommendations update in real time.


UI reflects the uploaded HTML prototype exactly.


Users can edit records manually.


Alerts and order recommendations update instantly.


The application should feel like:


Spreadsheet-powered


Operational


Real-time


Lightweight


Demoable within days


NOT enterprise-heavy.

2. Core Business Mental Model
This is fundamentally a:
“Demand Driven Inventory Planning System”
The Excel is performing DDMRP-style calculations.
The system determines:


How much stock exists


How much demand exists


How much buffer should exist


Whether replenishment is required


What quantity should be ordered



3. Canonical Ubiquitous Language
These terms MUST be used consistently across backend/frontend/database.
TermMeaningMSKUMaster SKUSKUSellable SKUADUAverage Daily UsageOHOn Hand InventoryOOOn Order InventoryQDQualified DemandNFNet FlowTORTop Of RedTOGTop Of GreenMOQMinimum Order QuantityDLTDecoupled Lead TimeLTFLead Time FactorVFVariability FactorDOCDesired Order CycleBuffer ZoneRed / Yellow / Green inventory rangeOrder RecommendationSuggested replenishment quantityUpload JobOne uploaded CSV/XLSX operationPlanning SnapshotDaily calculated inventory state

4. Existing Excel Logic Extracted
The Excel already contains the planning engine.
Key Formulas Identified
ADU
90 DAY SALES / 90
Yellow Zone
ADU * DOC
Red Base
ADU * DLT * LTF
Red Safety
RED BASE * VF
Red Zone
RED BASE + RED SAFETY
TOY
RED + YELLOW
TOG
RED + YELLOW + GREEN
Net Flow
(ON HAND + ON ORDER) - QUALIFIED DEMAND
Planning Priority
NET FLOW / TOG
Order Recommendation
TOG - NET FLOW

5. Existing HTML Modules
The uploaded HTML already defines the UX structure.
The app MUST preserve this structure.

6. Required Modules
6.1 Dashboard
Features


KPI cards


Alert counts


Inventory status


Healthy vs Red vs Yellow


Daily upload status


Recent uploads


Backend APIs
GET /api/dashboard

6.2 Stock Upload Module
HTML already defines:


Required columns


Drag/drop upload


Validation preview


Upload history


Required Upload Columns
ColumnRequiredMSKU_CODEYESOH_QTYYESDATEYESOO_QTYOptionalQD_QTYOptional

7. Upload Flow
Step 1 — User Uploads CSV/XLSX
Frontend:
Drag & DropORBrowse File

Step 2 — Backend Validation
Flask validates:
ValidationRuleRequired columnsMust existDuplicate MSKUsRejectInvalid datesRejectNegative quantitiesRejectUnknown MSKUsRejectEmpty rowsIgnore

Step 3 — Preview
Frontend shows:
✅ Rows valid✅ MSKUs matched⚠ Missing values❌ Invalid rows
Exactly like current HTML preview.

Step 4 — Commit Import
System writes to:


upload_jobs


inventory_snapshots


planning_snapshots


Then recalculates planning engine.

8. Real-Time Recalculation Engine
This is the HEART of the system.
Whenever:


upload occurs


edit occurs


parameter changes


System recalculates:
ADUREDYELLOWGREENTOGNET FLOWORDER RECOMMENDATIONALERTS

9. Minimal Real-Time Architecture
DO NOT OVERENGINEER.
Use:
Flask



Supabase



Lightweight polling
Frontend polling:
setInterval(fetchDashboard, 5000)
Enough for demo.
NO Kafka.
NO microservices.
NO event buses.

10. Frontend Architecture
Structure
/static    /css    /js/templates    dashboard.html    stock_upload.html    planning.html

11. Backend Architecture
Structure
/app    /routes    /services    /calculations    /repositories    /validators    /uploads

12. Database Design (Supabase)
12.1 msku_master
Single source of truth for SKUs.
Columnidmsku_codeproductstylefitbrandmoqlead_timeltfvfdltdocactive
Derived from upload structure in HTML. 

12.2 inventory_snapshots
Daily uploaded inventory.
Columnidmsku_codesnapshot_dateon_hand_qtyon_order_qtyqualified_demand_qtyuploaded_byupload_job_id

12.3 planning_snapshots
Calculated planning state.
Columnidmsku_codeadured_zoneyellow_zonegreen_zonetognet_flowplanning_priorityorder_recommendationalert_levelcalculated_at

12.4 upload_jobs
Tracks upload history.
Matches HTML upload history table. 
Columnidfilenameuploaded_byuploaded_atrow_countvalid_rowsinvalid_rowsstatus

12.5 alerts
Columnidmsku_codealert_typeseveritymessagecreated_atresolved

13. Alert Logic
Red Alert
NET FLOW < RED
Yellow Alert
NET FLOW between RED and TOY
Healthy
NET FLOW > TOY

14. Editable Data Requirements
Users must be able to edit:
EditableMOQVFLTFDOCLead TimeOn HandOn OrderQualified Demand
Every edit triggers recalculation.

15. What Should Be Dynamic
Dynamic
Dynamic FieldInventoryDemandAlertsBuffer zonesRecommendationsPlanning priority

16. What Should Be Configurable
Configurable
ParameterADU WindowMOQDLTLTFVFDOC
Found in PARAMETER sheet. 

17. What Should Be System Generated
Generated
GeneratedTOGTORRedYellowGreenNet FlowRecommendationAlerts

18. Required APIs
Upload
POST /api/uploads/stock

Dashboard
GET /api/dashboard

Planning Table
GET /api/planning

Update Planning Row
PUT /api/planning/{id}

Alerts
GET /api/alerts

Upload History
GET /api/uploads/history

19. CSV Processing Rules
CSV must support


UTF-8


XLSX


CSV



Parsing Library
Use:
pandasopenpyxl

20. Required Upload UX
The HTML already defines exact upload UX.
Must include:


Drag/drop


Validation summary


Import button


Template download


Upload history



21. Spreadsheet Preservation Strategy
DO NOT embed Excel formulas directly.
Instead:
Convert formulas into Python calculation service.
/calculations/ddmrp_engine.py
This becomes the SSOT.

22. DDMRP Engine Responsibilities
The engine calculates:
calculate_adu()calculate_red_zone()calculate_yellow_zone()calculate_green_zone()calculate_tog()calculate_net_flow()calculate_order_recommendation()calculate_alert_level()

23. Frontend Pages Required
PageDashboardPlanning TableStock UploadSKU UploadAlertsUpload History

24. Planning Table Requirements
Must support:


inline editing


sorting


filtering


search


color-coded alerts


live recalculation



25. UI Design Constraints
VERY IMPORTANT:
DO NOT redesign UI.
Use uploaded HTML structure exactly.
Only:


connect APIs


replace mock data


enable interactivity



26. Suggested Tech Stack
MVP
LayerTechFrontendHTML/CSS/JSBackendFlaskDatabaseSupabaseUpload ProcessingPandasAuthSupabase AuthDeploymentRender/Railway

27. Folder Structure
project/│├── app/│   ├── routes/│   ├── services/│   ├── calculations/│   ├── validators/│   ├── repositories/│   ├── uploads/│   └── templates/│├── static/│   ├── css/│   ├── js/│   └── uploads/│├── requirements.txt├── app.py└── .env

28. Task Breakdown For Coding Agent
PHASE 1 — Setup
Tasks


Flask app init


Supabase connection


HTML integration


Static asset serving



PHASE 2 — Database
Tasks


Create tables


Add indexes


Seed sample data



PHASE 3 — Upload Engine
Tasks


CSV upload endpoint


XLSX upload endpoint


Validation service


Upload history



PHASE 4 — DDMRP Engine
Tasks


Formula implementation


Recalculation engine


Alert engine



PHASE 5 — Frontend Binding
Tasks


Replace mock data


Connect APIs


Inline editing


Polling refresh



PHASE 6 — Demo Readiness
Tasks


Seed realistic data


Add loading states


Add upload success flows


Error handling



29. Demo Success Criteria
The system is successful if:
✅ Upload CSV works
✅ Dashboard updates automatically
✅ Alerts appear automatically
✅ Recommendations calculate automatically
✅ User can edit values
✅ HTML UI remains identical
✅ Upload history works
✅ Real-time refresh works
✅ Minimal but stable architecture

30. Final SSOT Principle
The FINAL source of truth is:
NOT Excel
NOT HTML
NOT frontend
The FINAL SSOT becomes:
Supabase database+Python DDMRP calculation engine
Excel becomes ONLY:
Input source

31. Migration Path
Current State
Static HTML + Excel formulas
Target State
Interactive real-time planning application

32. Implementation Priority
DO THESE FIRST:


Upload flow


Planning table


Calculation engine


Alerts


Dashboard


Everything else later.

33. Critical Engineering Rule
KEEP IT SIMPLE.
This is:


a planning demo


an operational prototype


not SAP


not Oracle SCM


Avoid:


microservices


complex architecture


AI layers


event streaming


heavy frameworks


Flask + Supabase + HTML is enough.