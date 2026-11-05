#!/usr/bin/env node
'use strict';
const fs = require('fs');
const model = require('../VeloAE/js/curve-model.js');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const state = model.normalize(input.state || input);
const result = {
  state,
  samples: model.sample(state, input.count || 257),
  nativeEase: state.mode === 'bezier' ? model.nativeEase(state, input.delta === undefined ? 100 : input.delta, input.duration || 1) : null
};
process.stdout.write(JSON.stringify(result));
