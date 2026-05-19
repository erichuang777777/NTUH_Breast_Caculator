window.NHI_APP_CONFIG = {
  release: '2026-05-19',
  layout: {
    mobileMaxWidth: 767
  },
  ajcc: {
    tOptions: [
      { label: 'T0', value: 'T0' },
      { label: 'Tis', value: 'Tis' },
      { label: 'T1', value: 'T1c' },
      { label: 'T2', value: 'T2' },
      { label: 'T3', value: 'T3' },
      { label: 'T4', value: 'T4' }
    ],
    nOptions: [
      { label: 'N0', value: 'N0' },
      { label: 'N1mi', value: 'N1mi' },
      { label: 'N1', value: 'N1' },
      { label: 'N2', value: 'N2a' },
      { label: 'N3', value: 'N3a' }
    ],
    mOptions: [
      { label: 'M0', value: 'M0' },
      { label: 'M1', value: 'M1' }
    ],
    gradeOptions: [
      { label: 'G1', value: '1' },
      { label: 'G2', value: '2' },
      { label: 'G3', value: '3' }
    ],
    markerOptions: {
      her2: [
        { label: 'HER2 +', value: '+' },
        { label: 'HER2 -', value: '-' }
      ],
      er: [
        { label: 'ER +', value: '+' },
        { label: 'ER -', value: '-' }
      ],
      pr: [
        { label: 'PR +', value: '+' },
        { label: 'PR -', value: '-' }
      ]
    },
    oncotypeOptions: [
      { label: '?', value: '' },
      { label: 'Oncotype DX RS <11', value: 'lt11', sub: 'Genomic Profile Low Risk' },
      { label: 'Oncotype DX RS >=11', value: 'ge11', sub: 'Genomic Profile High Risk' }
    ]
  }
};
