start: cycling_command

cycling_command: "role" ESCAPED_STRING "{" command* "}"

command: find_rider | find_team | find_race 
       | add_rider | modify_rider
       | add_team | modify_team  
       | add_race | modify_race
       | document_entity | link_entities

// Search operations
find_rider: "find_rider" "{" rider_search_criteria* "}"
find_team: "find_team" "{" team_search_criteria* "}"
find_race: "find_race" "{" race_search_criteria* "}"

// Add operations
add_rider: "add_rider" ESCAPED_STRING "{" rider_prop* "}"
add_team: "add_team" ESCAPED_STRING "{" team_prop* "}"
add_race: "add_race" ESCAPED_STRING "{" race_prop* "}"

// Modify operations
modify_rider: "modify_rider" NUMBER "{" rider_prop* "}"
modify_team: "modify_team" NUMBER "{" team_prop* "}"
modify_race: "modify_race" NUMBER "{" race_prop* "}"

// Special operations
document_entity: "document_entity" ESCAPED_STRING "{" doc_prop* "}"
link_entities: "link_entities" "{" link_prop* "}"

// Rider properties and search criteria
rider_prop: "first_name" ":" ESCAPED_STRING -> rider_first_name
          | "last_name" ":" ESCAPED_STRING -> rider_last_name
          | "country" ":" ESCAPED_STRING -> rider_country
          | "birth_date" ":" ESCAPED_STRING -> rider_birth_date
          | "team_id" ":" NUMBER -> rider_team
          | "rank" ":" NUMBER -> rider_rank
          | "points" ":" NUMBER -> rider_points
          | "documented" ":" CNAME -> rider_documented

rider_search_criteria: "name_pattern" ":" ESCAPED_STRING -> rider_name_pattern
                     | "country" ":" ESCAPED_STRING -> rider_country_filter
                     | "team_id" ":" NUMBER -> rider_team_filter
                     | "min_rank" ":" NUMBER -> rider_min_rank
                     | "max_rank" ":" NUMBER -> rider_max_rank
                     | "min_points" ":" NUMBER -> rider_min_points
                     | "max_points" ":" NUMBER -> rider_max_points
                     | "documented" ":" CNAME -> rider_documented_filter

// Team properties and search criteria
team_prop: "name" ":" ESCAPED_STRING -> team_name
         | "country" ":" ESCAPED_STRING -> team_country
         | "bike" ":" ESCAPED_STRING -> team_bike
         | "website" ":" ESCAPED_STRING -> team_website
         | "add_rider" ":" NUMBER -> team_add_rider
         | "remove_rider" ":" NUMBER -> team_remove_rider

team_search_criteria: "name_pattern" ":" ESCAPED_STRING -> team_name_pattern
                    | "country" ":" ESCAPED_STRING -> team_country_filter
                    | "bike" ":" ESCAPED_STRING -> team_bike_filter
                    | "has_rider" ":" NUMBER -> team_has_rider

// Race properties and search criteria
race_prop: "name" ":" ESCAPED_STRING -> race_name
         | "country" ":" ESCAPED_STRING -> race_country
         | "class" ":" ESCAPED_STRING -> race_class
         | "start_date" ":" ESCAPED_STRING -> race_start_date
         | "end_date" ":" ESCAPED_STRING -> race_end_date
         | "distance" ":" NUMBER -> race_distance

race_search_criteria: "name_pattern" ":" ESCAPED_STRING -> race_name_pattern
                    | "country" ":" ESCAPED_STRING -> race_country_filter
                    | "class" ":" ESCAPED_STRING -> race_class_filter
                    | "start_date" ":" ESCAPED_STRING -> race_start_date_filter
                    | "end_date" ":" ESCAPED_STRING -> race_end_date_filter
                    | "year" ":" NUMBER -> race_year_filter

// Documentation properties
doc_prop: "entity_type" ":" ESCAPED_STRING -> doc_entity_type
        | "entity_id" ":" NUMBER -> doc_entity_id

// Link properties
link_prop: "rider_id" ":" NUMBER -> link_rider_id
         | "team_id" ":" NUMBER -> link_team_id
         | "race_id" ":" NUMBER -> link_race_id

%import common.CNAME
%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS