/**
 * QRISK3-2017 coefficients and engine.
 *
 * Extracted from app.jsx (M6). Self-contained and clinically load-bearing: it
 * reproduces the algorithm's own published test vectors, and
 * tests/cvd/test_qrisk3.py asserts these coefficients match the backend's
 * character for character. Isolating it makes that comparison a file diff
 * rather than a search through three thousand lines.
 */
        //  alongside Indian guidance (Lipid Association of India / ICMR).
        const QRISK3_FEMALE = {
          survivor: 0.988876402378082,
          Iethrisk: [0, 0, 0.2804031433299542, 0.5629899414207540, 0.2959000085111652,
                     0.0727853798779825, -0.1707213550885732, -0.3937104331487497,
                     -0.3263249528353027, -0.1712705688324178],
          Ismoke: [0, 0.1338683378654626, 0.5620085801243854, 0.6674959337750255, 0.8494817764483085],
          c: { age1: -8.1388109247726188, age2: 0.7973337668969910,
               bmi1: 0.2923609227546005, bmi2: -4.1513300213837665,
               rati: 0.1533803582080255, sbp: 0.0131314884071034, sbps5: 0.0078894541014586,
               town: 0.0772237905885901, AF: 1.5923354969269663, atypicalantipsy: 0.2523764207011556,
               corticosteroids: 0.5952072530460185, migraine: 0.3012672608703450, ra: 0.2136480343518194,
               renal: 0.6519456949384583, semi: 0.1255530805882018, sle: 0.7588093865426769,
               treatedhyp: 0.5093159368342300, type1: 1.7267977510537347, type2: 1.0688773244615468,
               fh_cvd: 0.4544531902089621 },
          // age_1 (age1×var) and age_2 (age2×var) interaction terms
          i1: { s1: -4.7057161785851891, s2: -2.7430383403573337, s3: -0.8660808882939218, s4: 0.9024156236971065,
                AF: 19.9380348895465610, corticosteroids: -0.9840804523593628, migraine: 1.7634979587872999,
                renal: -3.5874047731694114, sle: 19.6903037386382920, treatedhyp: 11.8728097339218120,
                type1: -1.2444332714320747, type2: 6.8652342000009599, bmi1: 23.8026234121417420,
                bmi2: -71.1849476920870070, fh_cvd: 0.9946780794043513, sbp: 0.0341318423386155, town: -1.0301180802035639 },
          i2: { s1: -0.0755892446431930, s2: -0.1195119287486707, s3: -0.1036630639757192, s4: -0.1399185359171839,
                AF: -0.0761826510111625, corticosteroids: -0.1200536494674247, migraine: -0.0655869178986999,
                renal: -0.2268887308644251, sle: 0.0773479496790163, treatedhyp: 0.0009685782358817,
                type1: -0.2872406462448895, type2: -0.0971122525906955, bmi1: 0.5236995893366443,
                bmi2: 0.0457441901223238, fh_cvd: -0.0768850516984230, sbp: -0.0015082501423272, town: -0.0315934146749623 },
          center: { rati: 3.476326465606690, sbp: 123.130012512207030, sbps5: 9.002537727355957, town: 0.392308831214905 },
        };
        const QRISK3_MALE = {
          survivor: 0.977268040180206,
          Iethrisk: [0, 0, 0.2771924876030828, 0.4744636071493127, 0.5296172991968937,
                     0.0351001591862990, -0.3580789966932792, -0.4005648523216514,
                     -0.4152279288983017, -0.2632134813474997],
          Ismoke: [0, 0.1912822286338898, 0.5524158819264555, 0.6383505302750607, 0.7898381988185802],
          c: { age1: -17.8397816660055750, age2: 0.0022964880605765,
               bmi1: 2.4562776660536358, bmi2: -8.3011122314711354,
               rati: 0.1734019685632711, sbp: 0.0129101265425533, sbps5: 0.0102519142912905,
               town: 0.0332682012772873, AF: 0.8820923692805466, atypicalantipsy: 0.1304687985517351,
               corticosteroids: 0.4548539975044554, impotence2: 0.2225185908670538, migraine: 0.2558417807415991,
               ra: 0.2097065801395657, renal: 0.7185326128827438, semi: 0.1213303988204716, sle: 0.4401572174457522,
               treatedhyp: 0.5165987108269547, type1: 1.2343425521675175, type2: 0.8594207143093222,
               fh_cvd: 0.5405546900939016 },
          i1: { s1: -0.2101113393351635, s2: 0.7526867644750319, s3: 0.9931588755640579, s4: 2.1331163414389076,
                AF: 3.4896675530623207, corticosteroids: 1.1708133653489108, impotence2: -1.5064009857454310,
                migraine: 2.3491159871402441, renal: -0.5065671632722369, treatedhyp: 6.5114581098532671,
                type1: 5.3379864878006531, type2: 3.6461817406221311, bmi1: 31.0049529560338860,
                bmi2: -111.2915718439164300, fh_cvd: 2.7808628508531887, sbp: 0.0188585244698659, town: -0.1007554870063731 },
          i2: { s1: -0.0004985487027533, s2: -0.0007987563331739, s3: -0.0083706184266251, s4: -0.0007840031915564,
                AF: -0.0003499560834064, corticosteroids: -0.0002496045095297, impotence2: -0.0011058218441227,
                migraine: 0.0001989644604148, renal: -0.0018325930166499, treatedhyp: 0.0006383805310417,
                type1: 0.0006409780808753, type2: -0.0024695695588868, bmi1: 0.0050380102356322,
                bmi2: -0.0130744830025243, fh_cvd: -0.0002479180990740, sbp: -0.0000127187419159, town: -0.0000932996423233 },
          center: { rati: 4.300998687744141, sbp: 128.571578979492190, sbps5: 8.756621360778809, town: 0.526304900646210 },
        };

        // p = patient object. Returns 10-year CVD risk % (0–100) or null if age out of 25–84.
        function qrisk3(p) {
          const isFemale = p.sex === 'girls';
          const M = isFemale ? QRISK3_FEMALE : QRISK3_MALE;
          const age = p.age;
          if (!(age >= 25 && age <= 84)) return null;
          const bmiRaw = p.bmi;
          const bmi = Math.min(Math.max(bmiRaw, 20), 40);   // QRISK3 clamps BMI to [20,40]
          const dage = age / 10, dbmi = bmi / 10;

          // Fractional-polynomial transforms + centering (sex-specific for age).
          let age1, age2;
          if (isFemale) { age1 = Math.pow(dage, -2) - 0.053274843841791; age2 = dage - 4.332503318786621; }
          else          { age1 = Math.pow(dage, -1) - 0.234766781330109; age2 = Math.pow(dage, 3) - 77.284080505371094; }
          let bmi1, bmi2;
          if (isFemale) { bmi1 = Math.pow(dbmi, -2) - 0.154946178197861; bmi2 = Math.pow(dbmi, -2) * Math.log(dbmi) - 0.144462317228317; }
          else          { bmi1 = Math.pow(dbmi, -2) - 0.149176135659218; bmi2 = Math.pow(dbmi, -2) * Math.log(dbmi) - 0.141913309693336; }

          const rati = (typeof p.rati === 'number' ? p.rati : M.center.rati) - M.center.rati; // blank ⇒ 0 contribution
          const sbp  = (typeof p.sbp === 'number' ? p.sbp : M.center.sbp) - M.center.sbp;
          const sbps5 = (typeof p.sbps5 === 'number' ? p.sbps5 : 0) - M.center.sbps5;         // missing SD ⇒ 0 (QRISK convention)
          const town = (typeof p.town === 'number' ? p.town : 0) - M.center.town;             // UK-only ⇒ 0

          const c = M.c, i1 = M.i1, i2 = M.i2;
          let a = 0;
          a += M.Iethrisk[p.ethnicity || 1] || 0;
          a += M.Ismoke[p.smoke || 0] || 0;
          // continuous main effects
          a += age1 * c.age1 + age2 * c.age2 + bmi1 * c.bmi1 + bmi2 * c.bmi2;
          a += rati * c.rati + sbp * c.sbp + sbps5 * c.sbps5 + town * c.town;
          // binary main effects
          const B = {
            AF: p.af, atypicalantipsy: p.atypicalantipsy, corticosteroids: p.corticosteroids,
            migraine: p.migraine, ra: p.ra, renal: p.renal, semi: p.semi, sle: p.sle,
            treatedhyp: p.treatedhyp, type1: p.diabetes === 1, type2: p.diabetes === 2, fh_cvd: p.fh_cvd,
          };
          if (!isFemale) B.impotence2 = p.impotence2;
          for (const k in B) if (B[k] && typeof c[k] === 'number') a += c[k];
          // smoking × age interactions
          const sKey = ['', 's1', 's2', 's3', 's4'][p.smoke || 0];
          if (sKey) { a += age1 * (i1[sKey] || 0) + age2 * (i2[sKey] || 0); }
          // variable × age interactions (bmi + binary factors)
          a += age1 * (bmi1 * i1.bmi1 + bmi2 * i1.bmi2) + age2 * (bmi1 * i2.bmi1 + bmi2 * i2.bmi2);
          a += age1 * (sbp * i1.sbp) + age2 * (sbp * i2.sbp);
          a += age1 * (town * i1.town) + age2 * (town * i2.town);
          for (const k in B) {
            if (!B[k]) continue;
            if (typeof i1[k] === 'number') a += age1 * i1[k];
            if (typeof i2[k] === 'number') a += age2 * i2[k];
          }
          const risk = 100 * (1 - Math.pow(M.survivor, Math.exp(a)));
          return risk;
        }

        function normalCDF(z) {
          const t = 1 / (1 + 0.2316419 * Math.abs(z));
          const d = 0.39894228 * Math.exp(-z * z / 2);
          const p = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
          return z >= 0 ? 1 - p : p;
        }

        // Central-quartile -> standard-deviation factor. For a normal distribution
        // P75 and P25 sit at z = +/-0.6744898, so (P75 - P25) = 1.3489795 * SD.
        // The old code used (P75-P25)/2, which understates SD by ~1.48x and

export { QRISK3_FEMALE, QRISK3_MALE, qrisk3, normalCDF };
