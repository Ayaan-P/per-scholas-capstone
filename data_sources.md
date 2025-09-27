Based on extensive research, here's detailed API documentation for state, city, and county-level government funding
  sources:

  State-Level Grant APIs and Portals

  California Grants Portal

  - API Endpoint: data.ca.gov/dataset/california-grants-portal
  - Update Frequency: Every 24 hours at 8:45pm
  - Coverage: 161 current opportunities, $15.9B available funding
  - Data Access: CSV download, API calls via data.ca.gov "Explore" button
  - Total Allocated: $253B+ through 1,600+ grants from 70 state departments
  - Features: Filter by keywords, categories, applicant types (nonprofits, businesses, tribal governments)

  New York State Grants Management

  - System: Statewide Financial System (SFS)
  - Portal: grantsmanagement.ny.gov
  - Features: Grants Gateway enterprise system for viewing opportunities, managing applications
  - Email Alerts: Grant Notification System for new funding opportunities
  - API Access: Limited to registered organizations through SFS Vendor Portal

  Illinois GATA Portal

  - System: Grant Accountability and Transparency Act (GATA)
  - Portal: grants.illinois.gov/portal
  - Database: Catalog of State Financial Assistance (CSFA)
  - Features: Active grant programs, registered grantees, funding opportunities
  - Contact: OMB.GATA@illinois.gov
  - Registration: Required for grant management system access

  Massachusetts COMMBUYS

  - System: Commonwealth procurement portal
  - Features: Grant-specific UNSPSC codes, vendor registration, API services
  - Integration: Procurement data APIs available
  - Coverage: State contracts, grants, bid opportunities

  Texas Grant Systems

  - TEA Portal: TEAL (TEA Login) system for education grants
  - TDA-GO: Texas Department of Agriculture grants online system
  - TWC: Texas Workforce Commission grant opportunities
  - Coverage: Education, agriculture, workforce development funding

  Florida DOS Grants

  - Portal: dosgrants.com
  - Departments: Arts/Culture, Elections, Historical Resources, Library Services
  - Environmental: Florida DEP water resources grants portal
  - API: Limited government agency integration

  Georgia Grants Portal

  - Portal: cares.georgia.gov
  - System: GeorgiaGrants portal for awardees
  - Contact: grants@opb.georgia.gov, (404) 656-3820
  - Coverage: OPB competitive application processes

  Virginia Grant Resources

  - CDBG: DHCD Community Development Block Grants
  - VDSS: Virginia Department of Social Services block grants
  - GO Virginia: Grants database with economic development focus
  - Contact: CDBGProgram@dhcd.virginia.gov

  Ohio Grant Programs

  - System: No centralized API, multiple databases
  - SPIN: 40,000+ funding opportunities (OSU access)
  - OCOG: Ohio College Opportunity Grant
  - Coverage: Education, workforce development, community programs

  City-Level Grant Portals and APIs

  New York City

  - Benefits API: NYC Benefits Screening API for 40+ programs
  - NYCEDC: Federal/State Grants Engagement Portal
  - Features: Benefits screening without PII, quarterly updates
  - Coverage: SNAP, Cash Assistance, WIC, HEAP programs

  Los Angeles County

  - Economic Opportunity Grant: $50M+ invested through EOG Program
  - Portal: eog.smallbizla.org
  - Programs: ARPA, Keep LA Dining, COVID-19 Relief Funds
  - Partners: Lendistry application portal, SBDC assistance

  Chicago

  - Oracle Grants Management: iSupplier system for vendors
  - Portal: http://www.cityofchicago.org/eProcurement
  - Submittable: Free registration for grant applications
  - Programs: Community Development Grants, Neighborhood Opportunity Fund
  - Coverage: CDG awards, Small Business Improvement Fund

  Boston

  - Platform: WizeHive grant application system
  - Coverage: Workforce Development ($10M+ annually), Small Community Grants ($500-$2,000)
  - Programs: Life Sciences Workforce Development, Neighborhood Jobs Trust
  - Arts Funding: $3,000 project grants through Mayor's Office

  County-Level Funding Databases

  Cook County, Illinois

  - System: Enterprise Grants Management System (grants.cookcountyil.gov)
  - Programs: CDBG, ESG, Invest in Cook ($8.5M transportation grants)
  - API Access: USASpending API for federal grants data
  - Coverage: Community development, transportation, violence prevention

  Harris County, Texas

  - Office: Grants & Partnerships Division
  - Programs: Harris County Opportunity Fund ($5K-$250K loans), Harris Hub Program
  - Regional: H-GAC funding opportunities portal
  - Coverage: Small business recovery, disaster funding, ARPA investments

  Commercial Grant Database APIs

  Instrumentl

  - Coverage: 26,000+ grants by county/state
  - Features: AI matching, deadline tracking
  - API: Available in higher-tier plans
  - Statistics: 128,136 grants awarded in Texas (2023)

  GrantWatch

  - Coverage: State/county specific grant listings
  - Features: Daily email alerts, foundation databases
  - Access: Subscription-based, geographic filtering

  Federal API Integration Points

  Grants.gov API

  - Endpoint: v1/api/search2 (no authentication required)
  - Guide: grants.gov/api/api-guide
  - Features: Opportunity search, applicant/grantor endpoints

  SAM.gov APIs

  - Get Opportunities API: api.sam.gov/prod/opportunities/v2/search
  - Features: Federal procurement opportunities, contract notices
  - Parameters: NAICS codes, set-aside types, location filters

  USASpending API

  - Purpose: Federal grants data tracking
  - Integration: Used by Police Funding Database and other trackers
  - Coverage: All federal grant awards by jurisdiction

  Implementation Strategy for AdvancedDiscoveryEngine

  1. State Integration: Prioritize California, New York, Illinois, Massachusetts APIs for comprehensive coverage
  2. City Monitoring: NYC Benefits API, Boston WizeHive, Chicago Submittable for municipal opportunities
  3. County Tracking: Cook County and Harris County systems for large population centers
  4. Federal Baseline: Grants.gov and SAM.gov APIs for federal funding discovery
  5. Commercial Enhancement: Instrumentl API for AI-powered matching and comprehensive database access

  This documentation provides the foundation for expanding your AdvancedDiscoveryEngine beyond grants.gov to capture
  state, city, and county RFPs similar to those in your sample folder.