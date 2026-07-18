#!/usr/bin/env node
/**
 * TypeScript Type Generator from Supabase Database
 * 
 * This script connects to Supabase (local or remote) and generates
 * TypeScript types from the database schema using information_schema queries.
 * 
 * Usage:
 *   npm run generate:types
 *   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... npm run generate:types
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = resolve(__dirname, '../../../')

// Load environment variables from .env.local
function loadEnv(): void {
  const envPath = resolve(PROJECT_ROOT, '.env.local')
  if (existsSync(envPath)) {
    const envContent = readFileSync(envPath, 'utf-8')
    for (const line of envContent.split('\n')) {
      const [key, ...valueParts] = line.split('=')
      if (key && !key.startsWith('#')) {
        process.env[key.trim()] = valueParts.join('=').trim()
      }
    }
  }
}

loadEnv()

const SUPABASE_URL = process.env.SUPABASE_URL || 'http://127.0.0.1:54321'
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU'

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

interface ColumnInfo {
  table_name: string
  column_name: string
  data_type: string
  is_nullable: 'YES' | 'NO'
  column_default: string | null
  character_maximum_length: number | null
  numeric_precision: number | null
  numeric_scale: number | null
  udt_name: string
}

interface TableInfo {
  table_name: string
  columns: ColumnInfo[]
  primary_keys: string[]
  foreign_keys: ForeignKeyInfo[]
  indexes: IndexInfo[]
}

interface ForeignKeyInfo {
  column_name: string
  foreign_table_name: string
  foreign_column_name: string
  constraint_name: string
}

interface IndexInfo {
  index_name: string
  column_name: string
  is_unique: boolean
}

async function getDatabaseSchema(): Promise<TableInfo[]> {
  // Get all columns from information_schema
  const { data: columns, error: columnsError } = await supabase
    .from('information_schema.columns')
    .select('*')
    .eq('table_schema', 'public')
    .order('table_name')
    .order('ordinal_position')
  
  if (columnsError) throw columnsError
  
  // Get primary keys
  const { data: pkData, error: pkError } = await supabase
    .from('information_schema.table_constraints')
    .select('table_name, constraint_name')
    .eq('table_schema', 'public')
    .eq('constraint_type', 'PRIMARY KEY')
  
  if (pkError) throw pkError
  
  const { data: pkColumns, error: pkColsError } = await supabase
    .from('information_schema.key_column_usage')
    .select('table_name, constraint_name, column_name')
    .eq('table_schema', 'public')
  
  if (pkColsError) throw pkColsError
  
  // Get foreign keys
  const { data: fkData, error: fkError } = await supabase
    .from('information_schema.table_constraints')
    .select('table_name, constraint_name')
    .eq('table_schema', 'public')
    .eq('constraint_type', 'FOREIGN KEY')
  
  if (fkError) throw fkError
  
  const { data: fkColumns, error: fkColsError } = await supabase
    .from('information_schema.key_column_usage')
    .select('table_name, constraint_name, column_name, referenced_table_name, referenced_column_name')
    .eq('table_schema', 'public')
  
  if (fkColsError) throw fkColsError
  
  // Get indexes
  const { data: indexes, error: indexesError } = await supabase
    .from('pg_indexes')
    .select('indexname, tablename, indexdef')
    .eq('schemaname', 'public')
  
  if (indexesError) throw indexesError
  
  // Build table map
  const tableMap = new Map<string, TableInfo>()
  
  for (const col of columns || []) {
    if (!tableMap.has(col.table_name)) {
      tableMap.set(col.table_name, {
        table_name: col.table_name,
        columns: [],
        primary_keys: [],
        foreign_keys: [],
        indexes: []
      })
    }
    tableMap.get(col.table_name)!.columns.push({
      table_name: col.table_name,
      column_name: col.column_name,
      data_type: col.data_type,
      is_nullable: col.is_nullable,
      column_default: col.column_default,
      character_maximum_length: col.character_maximum_length,
      numeric_precision: col.numeric_precision,
      numeric_scale: col.numeric_scale,
      udt_name: col.udt_name
    })
  }
  
  // Add primary keys
  for (const pk of pkData || []) {
    const pkCols = pkColumns?.filter(c => c.constraint_name === pk.constraint_name && c.table_name === pk.table_name)
    if (pkCols && tableMap.has(pk.table_name)) {
      tableMap.get(pk.table_name)!.primary_keys = pkCols.map(c => c.column_name)
    }
  }
  
  // Add foreign keys
  for (const fk of fkData || []) {
    const fkCols = fkColumns?.filter(c => c.constraint_name === fk.constraint_name && c.table_name === fk.table_name)
    if (fkCols && tableMap.has(fk.table_name)) {
      for (const col of fkCols) {
        tableMap.get(fk.table_name)!.foreign_keys.push({
          column_name: col.column_name,
          foreign_table_name: col.referenced_table_name,
          foreign_column_name: col.referenced_column_name,
          constraint_name: fk.constraint_name
        })
      }
    }
  }
  
  // Add indexes
  for (const idx of indexes || []) {
    if (tableMap.has(idx.tablename)) {
      // Parse column names from indexdef (simplified)
      const match = idx.indexdef.match(/\((.*?)\)/)
      const columns = match ? match[1].split(',').map(c => c.trim()) : []
      for (const col of columns) {
        tableMap.get(idx.tablename)!.indexes.push({
          index_name: idx.indexname,
          column_name: col,
          is_unique: idx.indexdef.includes('UNIQUE')
        })
      }
    }
  }
  
  return Array.from(tableMap.values())
}

function mapPostgresTypeToTs(pgType: string, udtName: string, isNullable: boolean): string {
  const typeMap: Record<string, string> = {
    'uuid': 'string',
    'text': 'string',
    'varchar': 'string',
    'char': 'string',
    'bpchar': 'string',
    'integer': 'number',
    'int4': 'number',
    'int': 'number',
    'bigint': 'number',
    'int8': 'number',
    'smallint': 'number',
    'int2': 'number',
    'numeric': 'number',
    'decimal': 'number',
    'real': 'number',
    'float4': 'number',
    'double precision': 'number',
    'float8': 'number',
    'boolean': 'boolean',
    'date': 'string',
    'timestamp with time zone': 'string',
    'timestamp without time zone': 'string',
    'timestamptz': 'string',
    'time with time zone': 'string',
    'time without time zone': 'string',
    'timetz': 'string',
    'interval': 'string',
    'json': 'Record<string, unknown>',
    'jsonb': 'Record<string, unknown>',
    'uuid[]': 'string[]',
    'text[]': 'string[]',
    'integer[]': 'number[]',
    'bigint[]': 'number[]',
    'numeric[]': 'number[]',
    'boolean[]': 'boolean[]',
  }
  
  // Check for array types first
  if (pgType.endsWith('[]')) {
    const baseType = pgType.slice(0, -2)
    const tsBaseType = typeMap[baseType] || 'unknown'
    return `${tsBaseType}[]`
  }
  
  const tsType = typeMap[pgType] || typeMap[udtName] || 'unknown'
  return isNullable ? `${tsType} | null` : tsType
}

function toPascalCase(str: string): string {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('')
}

function generateTypeInterface(table: TableInfo): string {
  const typeName = toPascalCase(table.table_name)
  const lines: string[] = []
  
  // Main Row type
  lines.push(`interface ${typeName} {`)
  for (const col of table.columns) {
    const tsType = mapPostgresTypeToTs(col.data_type, col.udt_name, col.is_nullable === 'YES')
    const optional = col.is_nullable === 'YES' || col.column_default ? '?' : ''
    lines.push(`  ${col.column_name}${optional}: ${tsType}`)
  }
  lines.push('}')
  lines.push('')
  
  // Insert type (exclude auto-generated columns)
  const insertLines = [`interface ${typeName}Insert {`]
  for (const col of table.columns) {
    // Skip auto-generated columns
    if (table.primary_keys.includes(col.column_name) && col.udt_name === 'uuid') {
      continue
    }
    if (col.column_default && (
      col.column_default.includes('uuid_generate_v4') ||
      col.column_default.includes('gen_random_uuid') ||
      col.column_default.includes('now()') ||
      col.column_default.includes('CURRENT_TIMESTAMP')
    )) {
      continue
    }
    const tsType = mapPostgresTypeToTs(col.data_type, col.udt_name, true)
    const optional = col.is_nullable === 'YES' || col.column_default ? '?' : ''
    insertLines.push(`  ${col.column_name}${optional}: ${tsType}`)
  }
  insertLines.push('}')
  insertLines.push('')
  
  // Update type (all optional, exclude primary key and auto-generated)
  const updateLines = [`interface ${typeName}Update {`]
  for (const col of table.columns) {
    if (table.primary_keys.includes(col.column_name)) continue
    if (col.column_default && (
      col.column_default.includes('uuid_generate_v4') ||
      col.column_default.includes('gen_random_uuid') ||
      col.column_default.includes('now()') ||
      col.column_default.includes('CURRENT_TIMESTAMP')
    )) {
      continue
    }
    const tsType = mapPostgresTypeToTs(col.data_type, col.udt_name, true)
    updateLines.push(`  ${col.column_name}?: ${tsType}`)
  }
  updateLines.push('}')
  updateLines.push('')
  
  return [...lines, ...insertLines, ...updateLines].join('\n')
}

async function generateTypes(): Promise<void> {
  console.log('🔄 Connecting to Supabase...')
  console.log(`   URL: ${SUPABASE_URL}`)
  
  const tables = await getDatabaseSchema()
  console.log(`📊 Found ${tables.length} tables`)
  
  const projectRef = SUPABASE_URL.split('//')[1]?.split('.')[0] || 'unknown'
  
  let output = `/**
 * Supabase Database Schema Type
 * Generated from Supabase database
 * Project: ${projectRef}
 * 
 * This file exports ONLY the Database schema type for Supabase client.
 * Individual table types are defined in ./types/index.ts
 * Run 'npm run generate:types' to regenerate this file from Supabase.
 */

import type { Json } from './types';

// ============================================
// DATABASE SCHEMA TYPE (for Supabase client)
// ============================================

export interface Database {
  public: {
    Tables: {
`
  
  for (const table of tables) {
    const typeName = toPascalCase(table.table_name)
    output += `      ${table.table_name}: {\n`
    output += `        Row: ${typeName}\n`
    output += `        Insert: ${typeName}Insert\n`
    output += `        Update: ${typeName}Update\n`
    output += `        Relationships: [\n`
    
    for (const fk of table.foreign_keys) {
      output += `          {\n`
      output += `            foreignKeyName: "${fk.constraint_name}"\n`
      output += `            columns: ["${fk.column_name}"]\n`
      output += `            isOneToOne: false\n`
      output += `            referencedRelation: "${fk.foreign_table_name}"\n`
      output += `            referencedColumns: ["${fk.foreign_column_name}"]\n`
      output += `            relationshipType: "ManyToOne"\n`
      output += `          },\n`
    }
    
    output += `        ]\n`
    output += `      }\n`
  }
  
  output += `    }\n`
  output += `    Views: {}\n`
  output += `    Functions: {}\n`
  output += `    Enums: {}\n`
  output += `    CompositeTypes: {}\n`
  output += `  }\n`
  output += `}\n\n`
  
  // Add table type interfaces (internal, not exported)
  for (const table of tables) {
    output += generateTypeInterface(table)
  }
  
  // Write to file
  const outputPath = resolve(PROJECT_ROOT, 'packages/shared/src/database.ts')
  const outputDir = dirname(outputPath)
  
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true })
  }
  
  writeFileSync(outputPath, output)
  console.log(`✅ Types generated at: ${outputPath}`)
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  generateTypes().catch(err => {
    console.error('❌ Type generation failed:', err)
    process.exit(1)
  })
}

export { generateTypes, getDatabaseSchema }