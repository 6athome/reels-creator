const fs = require('node:fs');
const {createRequire} = require('node:module');

const fromCli = createRequire(require.resolve('@remotion/cli/package.json'));
const fromBundler = createRequire(fromCli.resolve('@remotion/bundler'));
const fromWebpack = createRequire(fromBundler.resolve('webpack'));
const fromSchemaUtils = createRequire(fromWebpack.resolve('schema-utils'));
const Ajv = fromSchemaUtils('ajv');
const schema = require('../config/reel-project.schema.json');
const validator = new Ajv({allErrors: true});
const validate = process.argv[3] === '--style'
  ? validator.compile({definitions: schema.definitions, $ref: '#/definitions/personalStyle'})
  : validator.compile(schema);

try {
  const plan = JSON.parse(fs.readFileSync(process.argv[2], 'utf8').replace(/^\uFEFF/, ''));
  if (!validate(plan)) {
    throw new Error(validate.errors.map((issue) =>
      (issue.instancePath || '/') + ' ' + issue.message +
      (issue.params.additionalProperty ? ' (' + issue.params.additionalProperty + ')' : '')
    ).join('\n'));
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
