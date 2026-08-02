"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";

// Client shell for an intercepted route: it owns only the open/close
// behaviour. The contents are server-rendered and passed in as children,
// so no card markup is built in the browser. Dismissing navigates back,
// which returns the user to the search results underneath.

interface RouteModalProps {
  title: string;
  children: ReactNode;
}

export function RouteModal({ title, children }: RouteModalProps) {
  const router = useRouter();

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) router.back();
      }}
    >
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[calc(90vh-8rem)]">{children}</ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
