'use client';

import React, { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchSkills, fetchStats } from '@/lib/api';
import { SkillCard } from '@/components/cards/SkillCard';
import { CascadeFilter, FilterState } from '@/components/features/filter/CascadeFilter';
import { SearchBar } from '@/components/features/SearchBar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BrainCircuit, Database, FileText } from 'lucide-react';
import { SkillItem, StatsResponse } from '@/lib/types';

export default function SkillsPage() {
  const [filters, setFilters] = useState<FilterState>({
    category: "All",
    role: "All",
    taskId: "All",
    classifications: []
  });
  const [searchQuery, setSearchQuery] = useState("");

  // Memoized filter handler to prevent infinite re-renders
  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
  }, []);

  const { data: skills, isLoading: isLoadingSkills } = useQuery({
    queryKey: ['skills'],
    queryFn: fetchSkills,
  });

  const { data: stats } = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: fetchStats,
    initialData: {
      total_resources: 0,
      total_tasks: 1350,
      free_resources: 0,
      classified_artifacts: 0,
      classifications: { replace: 0, augment: 0, remain_human: 0, new_task: 0 },
      resource_types: {},
      difficulty_levels: {},
      last_updated: ''
    }
  });

  // Filter skills based on Cascade + Search
  const filteredSkills = React.useMemo(() => {
    if (!skills) return [];

    return skills.filter((skill: SkillItem) => {
      // 1. Category Filter
      if (filters.category !== "All" && skill.category !== filters.category) return false;

      // 2. Role Filter (SkillItem name is the role name roughly, or checked via ID)
      // Since API structure links skills (roles) to categories, we filter if role is selected.
      // If a specific role is selected in dropdown, we only show that ONE card.
      if (filters.role !== "All" && skill.name !== filters.role) return false;

      // 3. Task Filter - NOTE: The skills endpoint returns ROLES, not TASKS.
      // If a TASK is selected, we should ideally show the role that contains it or filter deeply.
      // For now, if a Task is selected, we might want to still show the role it belongs to.
      // BUT, the user requirement says "Shows only tasks for that role". 
      // This implies the grid might need to switch to showing TASKS if we go deep enough?
      // Re-reading spec: "Evidence Display for Tasks... When viewing a DCWF task..."
      // The current page lists SKILLS (Roles). 
      // If the user selects a Task, we should probably filter to the Role that task belongs to.
      // Implementation assumption: The Roles list stays as Roles, but filtered.

      // 4. Classification Filter (Matches any of the checked ones)
      if (filters.classifications.length > 0) {
        // We check if the role has ANY tasks with these classifications?
        // Or if the role's primary classification matches?
        // The SkillItem has a 'classifications' count object.
        // Let's filter if the role has > 0 count for any selected classification type.
        const hasMatch = filters.classifications.some(cls => {
          // Map UI label to SkillItem key
          const key = cls as keyof typeof skill.classifications;
          return skill.classifications[key] > 0;
        });
        if (!hasMatch) return false;
      }

      // 5. Search Query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return skill.name.toLowerCase().includes(q) ||
          skill.id.toLowerCase().includes(q) ||
          skill.category.toLowerCase().includes(q);
      }

      return true;
    });
  }, [skills, filters, searchQuery]);

  return (
    <div className="space-y-8">
      {/* Dashboard Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Resources</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_resources || 0}</div>
            <p className="text-xs text-muted-foreground">Evidence collected</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Classified Tasks</CardTitle>
            <BrainCircuit className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_tasks || 0}</div>
            <p className="text-xs text-muted-foreground">DCWF tasks analyzed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">85%</div>
            <p className="text-xs text-muted-foreground">Across all models</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Skills Matrix</h2>
            <p className="text-muted-foreground">
              Explore how AI is impacting specific cybersecurity tasks and roles.
            </p>
          </div>
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            className="w-full md:w-[300px]"
            placeholder="Search roles..."
          />
        </div>

        <CascadeFilter onFilterChange={handleFilterChange} />

        {isLoadingSkills ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-[250px] w-full rounded-xl" />
            ))}
          </div>
        ) : (
          <>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filteredSkills.map((skill: SkillItem, index: number) => (
                <SkillCard key={`${skill.id}-${skill.slug}-${index}`} skill={skill} />
              ))}
            </div>
            {filteredSkills.length === 0 && (
              <div className="text-center py-20 text-muted-foreground">
                No skills found matching your criteria.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
