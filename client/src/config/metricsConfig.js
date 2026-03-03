// Metric configurations for different analysis tabs

export const EMS_METRICS_CONFIG = [
  { 
    key: 'arrival_to_offload', 
    label: 'Arrival to Offload', 
    description: 'Time from EMS arrival to patient offload',
    unit: 'min',
    countLabel: 'patients'
  },
  { 
    key: 'offload_to_clear', 
    label: 'Offload to Clear', 
    description: 'Time from patient offload to EMS crew clear',
    unit: 'min',
    countLabel: 'patients'
  },
  { 
    key: 'ems_total_minutes', 
    label: 'EMS Total Time', 
    description: 'Total time EMS crew spent at hospital',
    unit: 'min',
    countLabel: 'patients'
  },
  { 
    key: 'download_minutes', 
    label: 'Download Time', 
    description: 'Time spent downloading patient to hospital',
    unit: 'min',
    countLabel: 'patients'
  }
];

export const ED_FLOW_METRICS_CONFIG = [
  {
    key: 'door_to_bed',
    label: 'Door to Bed',
    description: 'Time from arrival to being placed in a treatment bed',
    unit: 'min',
    countLabel: 'patients'
  },
  {
    key: 'bed_to_doc',
    label: 'Bed to Doctor',
    description: 'Time from being placed in a bed to being seen by a physician',
    unit: 'min',
    countLabel: 'patients'
  },
  {
    key: 'doc_to_disp',
    label: 'Physicain Assessment to Disposition',
    description: 'Time from physician assessment to disposition decision',
    unit: 'min',
    countLabel: 'patients'
  },
  {
    key: 'disp_to_left_ed',
    label: 'Disposition to Left ED',
    description: 'Time from disposition decision to patient leaving the ED',
    unit: 'min',
    countLabel: 'patients'
  }

  
];

export const INPATIENT_METRICS_CONFIG = [
  {
    key: 'consult_minutes',
    label: 'Consult Time',
    description: 'Time for inpatient consultation to complete',
    unit: 'min',
    countLabel: 'consults'
  },
  {
    key: 'bed_wait_minutes',
    label: 'Bed Wait Time',
    description: 'Time waiting for inpatient bed availability',
    unit: 'min',
    countLabel: 'patients'
  }
];

export const LAB_DIAGNOSTIC_METRICS_CONFIG = [
  {
    key: 'lab_minutes',
    label: 'Lab Processing Time',
    description: 'Time for laboratory tests to be completed',
    unit: 'min',
    countLabel: 'tests'
  },
  {
    key: 'imaging_minutes',
    label: 'Imaging Time',
    description: 'Time for diagnostic imaging to be completed',
    unit: 'min',
    countLabel: 'studies'
  }
];

// Filter functions for different data types
export const FILTER_FUNCTIONS = {
  ems: (row) => row.is_ems === true,
  edFlow: (row) => true, // Include all patients for ED flow metrics
  inpatient: (row) => row.disposition === 'admit',
  lab: (row) => row.had_lab === true || row.had_imaging === true
};