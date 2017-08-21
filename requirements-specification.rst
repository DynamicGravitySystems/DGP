======================================
Gravity Processing and Analysis System
======================================
-----------------------------------
Software Requirements Specification
-----------------------------------

Overall Description
===================

User Classes and Characteristics
--------------------------------
There are three types of users that interact with the system differentiated by
the subset of product functions used.  The user classes are:

- Operator
- Scientist
- Engineer

The Operator uses the software to assess data set quality to ensure that the
systems are functioning nominally.

The Scientist uses the software to produce a gravity anomaly.  They will
also seek to compare data sets across flights, projects, and sensor systems.

The Engineer uses the software to evaluate hardware and software and to troubleshoot issues.

Functional Requirements
=======================

1. FR1
  - Description: The user shall be able to import gravity data. The user shall be able to choose file type and define the format.
  - Priority: High
  - Rationale: Required to process gravity data. Allowing the user to define the type and format reduces future work to incorporate other sensors or changes to file types and formats.
  - Dependencies: None

2. FR2
  - Description: The user shall be able to import position and attitude data. The user shall be able to choose file type and define the format.
  - Priority: High
  - Rationale: Required to process gravity data. Allowing the user to define the type and format reduces future work to incorporate other sensors or changes to file types and formats.
  - Dependencies: None

4. FR4
  - Description: The user shall be able to organize data by project and flight.
  - Priority: High
  - Rationale: This is a standard organizing principle.
  - Dependencies: None

5. FR5
  - Description: The user shall be able to import and compare multiple trajectories for a flight.
  - Priority: Medium
  - Rationale: For comparison of INS hardware and post-processing methods.
  - Dependencies: None

6. FR6
  - Description: The user shall be able to combine and analyze data across projects and flights.
  - Priority: Medium
  - Rationale: For comparison of line reflown, or to produce a grid of lines flown for a survey, for example.
  - Dependencies: None

7. FR7
  - Description: The user shall be able to select sections of a flight for processing.
  - Priority: High
  - Rationale: Necessary to properly process gravity.
  - Dependencies: None

8. FR8
  - Description: The user shall be able to plot all corrections.
  - Priority: High
  - Rationale: For troubleshooting, for example.
  - Dependencies: None

9. FR9
  - Description: The user shall be able to choose to plot any channel.
  - Priority: High
  - Rationale: For quality control of data, diagnostics, and performance assessment.
  - Dependencies: None

10. FR10
  - Description: The user shall be able to compare with lines and grids processed externally.
  - Priority: Medium
  - Rationale: For quality control of data, diagnostics, and performance assessment.
  - Dependencies: None

11. FR11
  - Description: The user shall be able to export data. The user shall be able to choose file type and define the format.
  - Priority: High
  - Rationale: For further processing or use in another system.
  - Dependencies: None

12. FR12
  - Description: The user shall be able to specify sensor-specific parameters.
  - Priority: High
  - Rationale: Required to process gravity data.
  - Dependencies: None

13. FR13
  - Description: The user shall be able to plot flight track on a map.
  - Priority: High
  - Rationale: To facilitate selection of sections for processing.
  - Dependencies: FR2

14. FR14
  - Description: The user shall be able to import a background image or data set as the background for the map.
  - Priority: Low
  - Rationale: To facilitate selection of sections for processing.
  - Dependencies: FR13

15. FR15
  - Description: The user shall be able to choose the method used to filter data and any associated parameters.
  - Priority: High
  - Rationale: To facilitate comparison of processing methods.
  - Dependencies: None

16. FR16
  - Description: The user shall be able to compute statistics for any channel.
  - Priority: High
  - Rationale: For quality control of data, diagnostics, and performance assessment.
  - Dependencies:

17. FR17
  - Description: The user shall be able to perform cross-over analysis.
  - Priority: Medium
  - Rationale: For quality control at the level of a whole survey.
  - Dependencies:

18. FR18
  - Description: The user shall be able to perform upward continuation.
  - Priority: Low
  - Rationale: For quality control at the level of a whole survey.
  - Dependencies:

19. FR19
  - Description: The user shall ble able to flag bad data within lines and choose whether to exclude from processing.
  - Priority: High
  - Rationale: For quality control of data, diagnostics, and performance assessment.
  - Dependencies:

20. FR20
  - Description: The user shall be able to import outside data sets (e.g., SRTM, geoid) for comparison with flown gravity.
  - Priority: High
  - Rationale: For quality control of data, diagnostics, and performance assessment.
  - Dependencies
