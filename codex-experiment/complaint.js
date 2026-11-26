/* Public portal links and a small, deliberately labeled demo lookup. */
const Complaint = (() => {
  const agencies = {
    gcc: { en: 'Greater Chennai Corporation', ta: 'பெருநகர சென்னை மாநகராட்சி', url: 'https://gccservices.in/pgr/registercomplaints', alternate: 'https://wa.me/919445061913', phone: '1913' },
    electricity: { en: 'TANGEDCO', ta: 'தமிழ்நாடு மின்சார வாரியம்', url: 'https://ccms.tangedco.org/tangedco-public/', alternate: 'https://wa.me/919498794987', phone: '9498794987' },
    metroWater: { en: 'Chennai Metro Water', ta: 'சென்னை குடிநீர் வாரியம்', url: 'https://cms-cmwssb.tn.gov.in/', alternate: 'https://wa.me/918144930308', remarksLimit: 200 },
    water: { en: 'TWAD PUNAL', ta: 'குடிநீர் வடிகால் வாரியம்', url: 'https://punal.tn.gov.in/grievance/#/', alternate: 'https://wa.me/919499991916' },
    ration: { en: 'Tamil Nadu Public Distribution System', ta: 'தமிழ்நாடு பொது விநியோகத் திட்டம்', url: 'https://www.tnpds.gov.in/', alternate: 'mailto:support@tnpds.com' },
    reopen: { en: 'CM Helpline · 1100', ta: 'முதல்வரின் முகவரி · 1100', url: 'https://cmhelpline.tnega.org/', alternate: 'mailto:cmcell@tn.gov.in', phone: '1100' },
    municipality: { en: 'Local civic body', ta: 'உள்ளாட்சி அமைப்பு' },
    waterAuthority: { en: 'Local water authority', ta: 'உள்ளூர் குடிநீர் அமைப்பு' },
  };

  const issues = [
    { key: 'streetlight', en: 'Streetlight outage', ta: 'தெருவிளக்கு எரியவில்லை', match: /street[ -]?lights?|theru vilakku|theruvilakku|தெருவிளக்கு|light podala/, route: 'municipality' },
    { key: 'electricity', en: 'Electrical wire fault', ta: 'மின் கம்பி பழுது', match: /transformer|loose wire|power line|electric pole|மின் கம்பி|டிரான்ஸ்பார்மர்/, route: 'electricity' },
    { key: 'sewage', en: 'Sewage overflow', ta: 'கழிவுநீர் வழிந்தோடுகிறது', match: /sewage|saakkadai|sakkadai|sewer|manhole|சாக்கடை|கழிவுநீர்/, route: 'waterAuthority' },
    { key: 'stormwater', en: 'Rainwater drainage issue', ta: 'மழைநீர் வடிகால் பிரச்சினை', match: /rain ?water|storm ?water|mazhai thanni|மழைநீர்/, route: 'municipality' },
    { key: 'road', en: 'Pothole', ta: 'சாலைப் பள்ளம்', match: /pothole|road hole|saalai pallam|சாலைப்? பள்ளம்/, route: 'municipality' },
    { key: 'water', en: 'Drinking water problem', ta: 'குடிநீர் பிரச்சினை', match: /kudineer|drinking water|water (?:supply|pipe|leak)|thanni vara[la]|குடிநீர்/, route: 'water' },
    { key: 'ration', en: 'Ration shop problem', ta: 'நியாய விலைக் கடை பிரச்சினை', match: /ration|arisi|fair price shop|ரேஷன்|நியாய விலை/, route: 'ration' },
    { key: 'garbage', en: 'Uncollected garbage', ta: 'அகற்றப்படாத குப்பை', match: /garbage|kuppai|rubbish|குப்பை/, route: 'municipality' },
  ];

  const places = [
    { name: 'Tower Park Back Side', ta: 'டவர் பார்க் பின்புறம்', city: 'Chennai', zone: '08', ward: '103', street: 'Vth Avenue', aliases: /tower park|டவர் பார்க்/, area: /anna nagar|அண்ணா நகர்/ },
    { name: 'Anna Arch', ta: 'அண்ணா வளைவு', city: 'Chennai', zone: '08', ward: '102', street: 'IIIrd Avenue', aliases: /anna arch|அண்ணா வளைவு/, area: /anna nagar|அண்ணா நகர்/ },
    { name: 'Vijayanagar Bus Stand', ta: 'விஜயநகர் பேருந்து நிலையம்', city: 'Chennai', zone: '13', ward: '178', street: 'Velachery Main Road', aliases: /vijaya\s*nagar|விஜயநகர்/, area: /velachery|வேளச்சேரி/ },
    { name: 'Phoenix Marketcity', ta: 'பீனிக்ஸ் மார்க்கெட்சிட்டி', city: 'Chennai', zone: '13', ward: '175', street: 'Velachery Main Road', aliases: /phoenix|பீனிக்ஸ்/, area: /velachery|வேளச்சேரி/ },
    { name: 'Anna Bus Stand', ta: 'அண்ணா பேருந்து நிலையம்', city: 'Madurai', aliases: /anna bus stand|அண்ணா பேருந்து/, area: /madurai|மதுரை/ },
    { name: 'Gandhipuram', ta: 'காந்திபுரம்', city: 'Coimbatore', aliases: /gandhi\s*puram|காந்திபுரம்/, area: /coimbatore|kovai|கோவை/ },
  ];

  const examples = {
    en: [
      'Anna Nagar Tower Park back side-la streetlight 5 naala eriyala, transformer wire vera loose-aa irukku.',
      'Velachery main road-la saakkadai overflow aaguthu, periya pothole irukku.',
      'Madurai Anna Bus Stand pakkam kudineer pipe உடைஞ்சு thanni waste aaguthu.',
    ],
    ta: [
      'அண்ணா நகர் டவர் பார்க் பின்புறம் தெருவிளக்கு எரியவில்லை. மின் கம்பி தளர்ந்து உள்ளது.',
      'வேளச்சேரி மெயின் ரோட்டில் சாக்கடை வழிகிறது. சாலைப் பள்ளம் இருக்கிறது.',
      'மதுரை அண்ணா பேருந்து நிலையம் அருகில் குடிநீர் குழாய் உடைந்து உள்ளது.',
    ],
  };
  const reopenExample = {
    en: 'Complaint GCC-20491 Velachery Vijayanagar Bus Stand kitta fix pannama close pannitanga. Kuppai innum irukku.',
    ta: 'வேளச்சேரி விஜயநகர் பேருந்து நிலையம் அருகில் குப்பை இன்னும் உள்ளது. GCC-20491 புகாரை தீர்க்காமல் மூடிவிட்டார்கள்.',
  };

  function folded(value) {
    return value.normalize('NFC').toLowerCase();
  }

  function findPlace(turns) {
    for (let index = turns.length - 1; index >= 0; index--) {
      const turn = folded(turns[index]);
      const exact = places.filter(place => place.aliases.test(turn));
      if (exact.length === 1) return { place: exact[0], choices: [] };
      if (exact.length) return { place: null, choices: exact };
      const nearby = places.filter(place => place.area.test(turn));
      if (nearby.length) return { place: null, choices: nearby };
    }
    return { place: null, choices: [] };
  }

  function interpret({ turns, mode, place: selectedPlace, withoutWard }) {
    const spoken = turns.join('\n');
    const transcript = folded(spoken);
    const matched = issues.filter(issue => issue.match.test(transcript));
    const references = spoken.match(/\b[A-Z]{2,10}-\d{3,}\b/gi) || [];
    const reference = references.at(-1)?.toUpperCase() || '';
    const { place: suggestedPlace, choices } = findPlace(turns);
    const place = selectedPlace || suggestedPlace;
    const result = { spoken, matched, reference, place, withoutWard, choices, step: 'review' };
    const remaining = transcript.replace(/\b[a-z]{2,10}-\d{3,}\b/g, '').replace(/complaint|reference|ticket|number|புகார்|எண்|[\p{P}\s]/gu, '');

    if (mode === 'reopen' && !reference) result.step = 'reference';
    else if (/drainage|வடிகால்/.test(transcript) && !matched.some(issue => ['sewage', 'stormwater'].includes(issue.key))) result.step = 'waterType';
    else if (!matched.length && mode !== 'reopen') result.step = 'issue';
    else if (mode === 'reopen' && !matched.length && !remaining) result.step = 'issue';
    else if (!place && !withoutWard && mode !== 'reopen') result.step = 'place';
    return result;
  }

  function draftsFor(result, mode) {
    const grouped = new Map();
    if (mode === 'reopen') grouped.set('reopen', result.matched);
    else {
      for (const issue of result.matched) {
        let route = issue.route;
        if (result.place?.city === 'Chennai') {
          if (route === 'municipality') route = 'gcc';
          if (route === 'waterAuthority' || route === 'water') route = 'metroWater';
        }
        if (route === 'water' && result.place?.city !== 'Madurai') route = 'waterAuthority';
        if (!grouped.has(route)) grouped.set(route, []);
        grouped.get(route).push(issue);
      }
    }
    return [...grouped].map(([route, matched]) => ({ agency: agencies[route], matched }));
  }

  return { interpret, draftsFor, examples, reopenExample };
})();

if (typeof module !== 'undefined') module.exports = Complaint;
